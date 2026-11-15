"""NASA monthly histories aggregated only over the explicitly requested complete periods."""

from calendar import monthrange
from datetime import date
import json
from pathlib import Path

import numpy as np
import requests
import yaml

from .assets import archive_response, system_trust_session
from .gaez import reference_cells
from .identity import fingerprint
from .model_records import model_record, persist_model_bundle, source_evidence
from .outcome_data import checked_bytes, write_json
from .storage_proof import require


MONTHLY = "https://power.larc.nasa.gov/api/temporal/monthly/regional"


def read_monthly(asset, parameter, start, end):
    data = json.loads(checked_bytes(asset))
    header = data["header"]
    require(header["start"] == f"{start}0101" and header["end"] == f"{end}1231",
            "NASA returned a different period; no temporal widening is allowed")
    require(header["time_standard"] == "LST" and "Monthly" in header["api"]["name"],
            "Source is not the requested monthly LST product")
    require(set(data["parameters"]) == {parameter} and data["parameters"][parameter]["units"],
            "NASA parameter/unit does not match the requested feature")
    require(data["type"] == "FeatureCollection" and data["features"], "NASA regional response has no grid points")
    positions = [tuple(feature["geometry"]["coordinates"][:2]) for feature in data["features"]]
    require(len(set(positions)) == len(positions), "NASA returned duplicate native grid points")
    axes = [sorted({position[index] for position in positions}) for index in (0, 1)]
    require(all(len(axis) >= 2 for axis in axes), "Insufficient source grid metadata")
    spacing = [min(np.diff(axis)) for axis in axes]
    require(all(np.allclose(np.diff(axis) / step, np.round(np.diff(axis) / step)) for axis, step in zip(axes, spacing)),
            "Irregular source grid needs an explicit spatial method")
    return data, [float(value) for value in spacing]


def acquire_india_environment(config_path, gaez_corpus, output, resume=False):
    config = yaml.safe_load(Path(config_path).read_bytes())
    spec, periods = config["nasa_reference"], config["gaez"]["periods"]
    reference = json.loads(Path(gaez_corpus).read_bytes())
    cells = reference_cells(reference)
    output = Path(output)
    if resume:
        corpus = json.loads((output / "corpus.json").read_bytes())
        require(corpus["specification"] == spec and corpus["periods"] == periods, "A resumed NASA request cannot change scope")
    else:
        output.mkdir(parents=True, exist_ok=False)
        corpus = {"schema_version": "1", "kind": "india_nasa_monthly_corpus", "status": "in_progress",
                  "specification": spec, "periods": periods, "assets": [], "reports": []}
    cache = {asset["requested_url"]: asset for asset in corpus["assets"]}
    try:
        with system_trust_session() as session:
            reports = []
            for parameter, requested_periods in spec["parameters"].items():
                require(set(requested_periods) <= periods.keys(), "Unknown environmental period")
                start = min(periods[period][0] for period in requested_periods)
                end = max(periods[period][1] for period in requested_periods)
                west, south, east, north = spec["bounds"]
                for bottom in range(south, north, 10):
                    top = min(bottom + 10, north)
                    for left in range(west, east, 10):
                        right = min(left + 10, east)
                        if not any(left <= cell["longitude"] <= right and bottom <= cell["latitude"] <= top for cell in cells):
                            continue
                        require(2 <= right - left <= 10 and 2 <= top - bottom <= 10, "NASA requires explicit 2-10 degree regional extents")
                        params = {"latitude-min": bottom, "latitude-max": top, "longitude-min": left, "longitude-max": right,
                                  "parameters": parameter, "community": "AG", "format": "JSON", "start": start, "end": end}
                        url = requests.Request("GET", MONTHLY, params=params).prepare().url
                        corpus["active_request"] = params
                        write_json(output / "corpus.json", corpus)
                        if url in cache:
                            asset = cache[url]
                            checked_bytes(asset)
                        else:
                            asset = archive_response(MONTHLY, output / "raw", params=params, session=session, timeout=180)
                            corpus["assets"].append(asset)
                            cache[url] = asset
                            write_json(output / "corpus.json", corpus)
                        read_monthly(asset, parameter, start, end)
                        reports.append({"parameter": parameter, "periods": requested_periods, "start": start, "end": end, "asset": asset})
            corpus["reports"] = reports
        corpus["status"] = "complete"
        corpus.pop("active_request", None)
        corpus.pop("error_type", None)
        write_json(output / "corpus.json", corpus)
        return output / "corpus.json"
    except Exception as error:
        corpus.update(status="failed", error_type=type(error).__name__)
        write_json(output / "corpus.json", corpus)
        raise


def build_india_environment(corpus_path, output, store):
    corpus = json.loads(Path(corpus_path).read_bytes())
    require(corpus["kind"] == "india_nasa_monthly_corpus" and corpus["status"] == "complete", "NASA acquisition is incomplete")
    require({item["parameter"] for item in corpus["reports"]} == set(corpus["specification"]["parameters"]),
            "Requested NASA parameters are absent from the captured corpus")
    records, evidence, contexts = {}, [], {}
    for report in corpus["reports"]:
        parameter, asset = report["parameter"], report["asset"]
        require(report["periods"] == corpus["specification"]["parameters"][parameter],
                "Captured NASA periods differ from the acquisition contract")
        data, spacing = read_monthly(asset, parameter, report["start"], report["end"])
        unit, fill = data["parameters"][parameter]["units"], data["header"]["fill_value"]
        for index, feature in enumerate(data["features"]):
            longitude, latitude = map(float, feature["geometry"]["coordinates"][:2])
            support = "power-grid-" + fingerprint([longitude, latitude, spacing])
            monthly = feature["properties"]["parameter"][parameter]
            for period in report["periods"]:
                start, end = corpus["periods"][period]
                require(report["start"] <= start <= end <= report["end"], "Normal extends beyond the captured monthly window")
                keys = [f"{year}{month:02d}" for year in range(start, end + 1) for month in range(1, 13)]
                weights = [monthrange(int(key[:4]), int(key[4:]))[1] for key in keys]
                values = [monthly.get(key) for key in keys]
                valid = [value is not None and value != fill and np.isfinite(value) for value in values]
                value = float(np.average(values, weights=weights)) if all(valid) else None
                record = model_record("climate_normal", ["nasa_power", support, parameter, period, "LST"], {
                    "source_id": "nasa_power", "metric_id": parameter, "period_id": period,
                    "longitude": longitude, "latitude": latitude, "source_grid_spacing_degrees": spacing,
                    "window_start": date(start, 1, 1).isoformat(), "window_end": date(end, 12, 31).isoformat(),
                    "time_standard": "LST", "temporal_support": "complete_monthly_history_derived_normal",
                    "evidence_type": "derived", "source_products": data["header"]["sources"], "value": value, "unit": unit,
                    "aggregation": "calendar_day_weighted_mean_of_monthly_values",
                    "valid_months": int(sum(valid)), "expected_months": len(keys),
                    "availability": "available" if value is not None else "incomplete_requested_window",
                }, support)
                previous = contexts.setdefault(record["context_id"], record["record_id"])
                require(previous == record["record_id"], "Overlapping NASA requests contain inconsistent native-cell values")
                records[record["record_id"]] = record
                evidence.append(source_evidence(record, asset, f"features:{index}:parameter:{parameter}:{keys[0]}-{keys[-1]}"))
    return persist_model_bundle(store, output, "india_nasa_reference_dataset", {
        "schema_version": "1", "periods": corpus["periods"], "time_standard": "LST",
        "temporal_widening": False, "missing_month_imputation": False, "native_grid_retained": True,
        "field_measurements": False, "attribution": "NASA POWER Project, NASA Langley Research Center.",
        "parameters": corpus["specification"]["parameters"], "source_reference": MONTHLY,
    }, corpus, list(records.values()), evidence)
