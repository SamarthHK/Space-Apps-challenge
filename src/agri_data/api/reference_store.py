"""One explicitly pinned, read-only reference model per API process."""

from contextlib import contextmanager
from hashlib import sha256
import json
from threading import Lock

from agri_data.contracts.india_inference_contract import ReferenceContextNotFound, ReferenceIntervalMismatch

from .pagination import Pagination


class ReferenceServiceError(Exception):
    def __init__(self, status, code, message, retryable=False):
        super().__init__(message)
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


class ReferenceStore:
    def __init__(self, settings):
        self.settings = settings
        self.pagination = Pagination()
        self._lock = Lock()
        self._model = None
        self._failed = False
        self._signatures = None
        self._serving_hashes = None

    @staticmethod
    def _unavailable():
        return ReferenceServiceError(503, "reference_model_unavailable",
                                     "The configured reference model is unavailable; verify operator setup and restart")

    def _sign(self, names):
        result = {}
        for name in names:
            path = (self.settings.model_dir / name).resolve()
            if path.parent != self.settings.model_dir:
                raise self._unavailable()
            stat = path.stat()
            result[name] = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_ino)
        return result

    def _check_files(self):
        if self._sign(self._signatures) != self._signatures:
            raise self._unavailable()
        for name, digest in self._serving_hashes.items():
            if sha256((self.settings.model_dir / name).read_bytes()).hexdigest() != digest:
                raise self._unavailable()

    def _load(self):
        import psutil
        from agri_data.contracts.model_resources import admit

        admit(1024 ** 3 if self._model is None else 8 * 1024 ** 2,
              {"available_ram_bytes": psutil.virtual_memory().available})
        if self._model is None:
            from agri_data.contracts.india_inference import ReferenceModel
            manifest_path = self.settings.model_dir / "manifest.json"
            raw_manifest = manifest_path.read_bytes()
            manifest = json.loads(raw_manifest)
            before = self._sign(["manifest.json", *manifest["files"]])
            loaded = ReferenceModel(self.settings.model_dir, self.settings.model_id)
            if self._sign(before) != before or manifest != loaded.manifest:
                raise self._unavailable()
            method = manifest["champion"]
            members = {"contexts.parquet", "crops.parquet", "example_request.json",
                       method + ".state.json", method + ".calibration.json"}
            if method != "baseline":
                members.add(method + (".cbm" if method == "catboost" else ".pt"))
            self._serving_hashes = {name: manifest["files"][name] for name in members}
            self._serving_hashes["manifest.json"] = sha256(raw_manifest).hexdigest()
            self._signatures, self._model = before, loaded
        self._check_files()
        return self._model

    @contextmanager
    def access(self, model_id=None):
        if self.settings is None:
            raise ReferenceServiceError(503, "reference_model_unconfigured",
                                        "Reference suitability is not configured")
        if model_id is not None and model_id != self.settings.model_id:
            raise ReferenceServiceError(409, "reference_model_changed",
                                        "The requested model is not configured; refresh reference model metadata")
        if not self._lock.acquire(blocking=False):
            raise ReferenceServiceError(503, "reference_model_busy",
                                        "Another reference-model operation is running; retry this read later", True)
        try:
            if self._failed:
                raise self._unavailable()
            try:
                loaded = self._load()
            except Exception:
                self._failed, self._model = True, None
                raise self._unavailable() from None
            try:
                yield loaded
            except ReferenceServiceError:
                raise
            except Exception:
                self._failed, self._model = True, None
                raise self._unavailable() from None
        finally:
            self._lock.release()

    def capability(self):
        try:
            with self.access():
                return "ready", None
        except ReferenceServiceError as error:
            return "blocked", error.message

    def metadata(self):
        with self.access() as loaded:
            manifest, state = loaded.manifest, loaded.state
            support = {tuple(pair) for pair in state["crop_system_support"]}
            crops = [{"crop_id": crop, "display_name": row["display_name"], "crop_group": row["crop_group"],
                      "production_systems": sorted(system for code, system in support if code == crop)}
                     for crop, row in loaded.crops.sort_index().iterrows()
                     if any(code == crop for code, _ in support)]
            example = json.loads((self.settings.model_dir / "example_request.json").read_bytes())
            return {
                "schema_version": "1", "model_id": manifest["model_id"], "dataset_id": manifest["dataset_id"],
                "task": manifest["task"], "mode": "historical_reference_analysis",
                "comparison_scope": "reference_climate_only", "method": manifest["champion"],
                "reference_score_unit": "GAEZ_suitability_index_rescaled_0_to_100",
                "preference_semantics": "relative_GAEZ_reference_preference_not_probability_of_farming_success",
                "periods": [{"period_id": period, "analysis_start": f"{start}-01-01", "analysis_end": f"{end}-12-31"}
                            for period, (start, end) in sorted(manifest["periods"].items())],
                "crops": crops, "context_count": len(loaded.contexts), "maximum_candidates": 100,
                "operational_recommendation_ready": False, "rotation_effects_supported": False,
                "preplant_supported": False, "strict_as_of_supported": False,
                "unassessed_requirement_axes": manifest["missing_requirement_axes"],
                "attribution": manifest["attribution"],
                "example_request": {**example, "model_id": manifest["model_id"]},
            }

    def contexts(self, model_id, period_id):
        with self.access(model_id) as loaded:
            if period_id is not None and period_id not in loaded.manifest["periods"]:
                raise ReferenceServiceError(422, "unsupported_reference_period",
                                            "Select a period declared by the reference model")
            rows = loaded.contexts.sort_index()
            if period_id is not None:
                rows = rows[rows.period_id == period_id]
            fields = ["context_id", "site_id", "latitude", "longitude", "analysis_start", "analysis_end", "period_id"]
            return [{**row, "support": "native_5_arcminute_GAEZ_reference_cell"}
                    for row in rows[fields].to_dict("records")]

    def predict(self, payload):
        with self.access(payload["model_id"]) as loaded:
            values = {key: value for key, value in payload.items() if key != "model_id"}
            try:
                return loaded.predict(values)
            except ReferenceContextNotFound:
                raise ReferenceServiceError(404, "reference_context_not_found",
                                            "The saved reference context does not exist") from None
            except ReferenceIntervalMismatch:
                raise ReferenceServiceError(422, "reference_interval_mismatch",
                                            "The analysis interval must match the saved reference context") from None
