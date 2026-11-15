"""Engineering checks for implemented routes, separate from scientific approval."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
import yaml

from .boundary_import import ingest_boundaries
from .canonical import reconcile_reference
from .corpus import COLLECTION, acquire_reference_corpus
from .identity import fingerprint
from .ml_dataset import export_preparation
from .postgres import PostgresStore
from .storage_proof import require, run_storage_proof
from .trials import acquire_woburn, import_woburn


def check_snapshot(path):
    """Check format/relationships without admitting the snapshot for training."""
    path = path.resolve()
    manifest = json.loads((path / "manifest.json").read_bytes())
    require(manifest["kind"] == "ml_dataset_preparation", "Unexpected dataset format")
    listed = {}
    for item in manifest["files"]:
        file = (path / item["path"]).resolve()
        require(file.parent == path and file.name not in listed, "Invalid or duplicate manifest path")
        require(sha256(file.read_bytes()).hexdigest() == item["sha256"], "Export checksum mismatch")
        listed[file.name] = file
        if item["row_count"] is not None:
            require(len(pd.read_parquet(file)) == item["row_count"], "Export row count mismatch")
    tables = {name: pd.read_parquet(listed[name + ".parquet"]) for name in (
        "examples", "features", "targets", "splits", "lineage", "weather",
    )}
    examples, targets, weather = (tables[name] for name in ("examples", "targets", "weather"))
    require(len(examples) > 0 and len(weather) > 0, "No records available to check")
    require(not examples[["example_id", "context_id"]].isna().any().any(), "Missing example identity")
    require(not examples["example_id"].duplicated().any(), "Duplicate example")
    require(not examples["context_id"].duplicated().any(), "Duplicate trial context")
    ids = set(examples["example_id"])
    for name in ("targets", "splits"):
        table = tables[name]
        require(not table["example_id"].duplicated().any(), f"Duplicate {name} rows")
        require(set(table["example_id"]) == ids, f"{name} example relationships differ")
    require(set(tables["features"]["example_id"]) == ids, "Feature relationships differ")
    require(not tables["features"][["example_id", "feature_id"]].duplicated().any(),
            "Duplicate feature per example")
    require(not targets["outcome_id"].duplicated().any(), "Duplicate target outcome")
    require(targets["unit"].eq("kg/ha").all(), "Unexpected yield unit")
    require(targets["value"].isna().equals(targets["availability"].eq("missing")),
            "Missing targets lost their explicit availability state")
    require(not weather["canonical_observation_id"].duplicated().any(), "Duplicate canonical weather")
    for row in weather.itertuples(index=False):
        record = json.loads(row.scientific_record_json)
        require(fingerprint(record) == row.canonical_observation_id, "Canonical content identity mismatch")
        require(record["field_id"] == row.field_id and record["variable_id"] == row.variable_id,
                "Canonical context columns differ from the record")
    lineage = tables["lineage"]
    require(not lineage.duplicated().any(), "Duplicate lineage receipt")
    for kind, identifiers in (
        ("target", set(targets["outcome_id"])),
        ("weather", set(weather["canonical_observation_id"])),
    ):
        require(set(lineage.loc[lineage["record_kind"] == kind, "record_id"]) == identifiers,
                f"Missing or orphan {kind} lineage")
    assets = json.loads(listed["assets.json"].read_bytes())
    for asset in assets:
        require(sha256(Path(asset["path"]).read_bytes()).hexdigest() == asset["sha256"],
                "Original asset checksum mismatch")
    require(set(lineage["raw_sha256"]) <= {asset["sha256"] for asset in assets},
            "Lineage references an unlisted source")
    return {
        "examples": len(examples), "canonical_weather": len(weather),
        "missing_yields": int(targets["value"].isna().sum()),
        "files_verified": len(listed), "training_ready": manifest["training_ready"],
        "scientific_approval_required": False,
    }


def run_health(config_path, output, repository):
    """Exercise real acquisition, imports and exports; never generate substitutes."""
    try:
        config = yaml.safe_load(config_path.read_bytes())
    except yaml.YAMLError as error:
        raise ValueError("Invalid YAML configuration") from error
    require(isinstance(config, dict) and config.get("schema_version") == "1",
            "Configuration needs schema_version: '1'")
    database = config["database"]
    require(isinstance(database, dict) and all(
        isinstance(database.get(key), str) and database[key].strip()
        for key in ("expected_database", "expected_user", "acceptance_schema", "connection_environment_variable")
    ), "Database configuration is incomplete")
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    results, values = [], {}
    actions = {
        "database_connection": "Check the configured database identity, connection environment, credentials and running server.",
        "live_reference": "Inspect fresh PDOK/NASA request receipts in data/raw/authentic-reference-corpus/raw.",
        "live_trial": "Inspect fresh Rothamsted request receipts in data/raw/rotation-trials/raw.",
        "boundary_pipeline": "Inspect boundaries/failure.json and the original KML; do not replace a rejected boundary.",
        "weather_pipeline": "Inspect weather/failure.json and the source response; check its format and database readback.",
        "trial_pipeline": "Check the trial archive schema/version, original values and database constraints.",
        "dataset_integrity": "Check failed/incomplete jobs, canonical links and dataset file hashes and relationships.",
    }

    def check(name, action, dependencies=()):
        if any(dependency not in values for dependency in dependencies):
            results.append({"check": name, "status": "blocked", "dependencies": list(dependencies)})
            return
        try:
            value = action()
            values[name] = value
            results.append({"check": name, "status": "passed"})
        except Exception as error:
            # Driver/network messages can include credentials; preserve type and
            # stage, with public request receipts in the acquisition directories.
            results.append({"check": name, "status": "failed", "error_type": type(error).__name__,
                            "next_action": actions[name]})

    def connect():
        store = PostgresStore(database["expected_database"], database["expected_user"],
                              database["acceptance_schema"], database["connection_environment_variable"])
        store.identity()
        return store

    check("database_connection", connect)
    check("live_reference", lambda: acquire_reference_corpus(
        repository / "data" / "raw" / "authentic-reference-corpus"))
    check("live_trial", lambda: acquire_woburn(repository / "data" / "raw" / "rotation-trials"))

    def boundary():
        corpus = values["live_reference"]
        result = ingest_boundaries(
            Path(corpus["kml_path"]), "public_reference", COLLECTION,
            corpus["boundary_source"], values["database_connection"], output / "boundaries",
            repository / "data" / "raw" / "boundary-imports",
        )
        require(result["status"] == "complete", "Boundary import did not complete")
        return result

    check("boundary_pipeline", boundary, ("database_connection", "live_reference"))
    check("weather_pipeline", lambda: run_storage_proof(
        Path(values["live_reference"]["manifest"]), values["database_connection"],
        output / "weather", repository,
    ), ("boundary_pipeline",))

    def trial():
        store, manifest = values["database_connection"], values["live_trial"]
        result = import_woburn(store, manifest)
        repeated = import_woburn(store, manifest)
        require(result["persisted"] > 0 and repeated["inserted"] == 0,
                "Trial import was empty or not idempotent")
        return result

    check("trial_pipeline", trial, ("database_connection", "live_trial"))

    def dataset():
        store = values["database_connection"]
        counts = reconcile_reference(store, Path(values["live_reference"]["manifest"]))
        require(counts["source_observations"] == counts["evidence_links"],
                "Unlinked source observations")
        with store.session(repeatable_read=True) as connection:
            unfinished = connection.execute(
                "SELECT count(*) FROM extraction_jobs WHERE status<>'complete'"
            ).fetchone()[0]
            require(unfinished == 0, "Failed or unfinished extraction jobs remain")
            duplicate = connection.execute(
                "SELECT count(*) FROM (SELECT scientific_record FROM canonical_observations "
                "GROUP BY scientific_record HAVING count(*)>1) duplicates"
            ).fetchone()[0]
            require(duplicate == 0, "Repeated canonical content")
            aliased = connection.execute(
                "SELECT count(*) FROM canonical_observations c JOIN field_aliases a "
                "ON c.field_id=a.alias_field_id"
            ).fetchone()[0]
            require(aliased == 0, "Canonical records still use historical aliases")
        export_preparation(store, repository / "config" / "ml_dataset.yaml", output / "dataset", repository)
        formats = check_snapshot(output / "dataset")
        require(formats["canonical_weather"] == counts["canonical_observations"],
                "Canonical database/export count mismatch")
        with store.session() as connection:
            outcomes = connection.execute("SELECT count(*) FROM crop_performance").fetchone()[0]
        require(formats["examples"] == outcomes, "Trial database/export count mismatch")
        return {"counts": counts, "format_checks": formats}

    check("dataset_integrity", dataset, ("weather_pipeline", "trial_pipeline"))
    receipts = []
    if "live_reference" in values:
        receipts.extend(values["live_reference"][key] for key in
                        ("collection_metadata", "parcel_asset", "weather_asset"))
    if "live_trial" in values:
        trial_manifest = json.loads(values["live_trial"].read_bytes())
        receipts.extend(trial_manifest[key] for key in ("landing", "terms", "data"))
    report = {
        "schema_version": "1", "profile": "engineering",
        "status": "passed" if all(row["status"] == "passed" for row in results) else "failed",
        "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
        "scientific_approval_required": False, "full_inventory_complete": False,
        "scope": ["PDOK reference boundary", "NASA POWER seven daily parameters", "Woburn trial import"],
        "checks": results, "verified_fresh_requests": len(receipts),
        "request_evidence": receipts,
        "data": values.get("dataset_integrity"),
        "limitations": [
            "Only the named implemented routes and acquired contexts are tested, not the full inventory.",
            "Reachability is measured during this run, not guaranteed for future provider requests.",
            "Scientific review status is retained but does not block engineering health.",
            "Dataset preparation is not an executable crop-rotation model or approval to train.",
        ],
        "report_path": str((output / "health.json").resolve()),
    }
    (output / "health.json.pending").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    (output / "health.json.pending").replace(output / "health.json")
    return report
