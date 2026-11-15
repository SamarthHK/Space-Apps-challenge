"""Reproducible decision-dataset preparation; pending evidence cannot train a model."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
import yaml

from .identity import fingerprint
from .trials import ACKNOWLEDGEMENT, ATTRIBUTION, CITATION


class DecisionExample(BaseModel):
    model_config = ConfigDict(extra="forbid")
    example_id: str = Field(min_length=1)
    site_id: str = Field(min_length=1)
    trial_id: str = Field(min_length=1)
    group_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    crop_id: str = Field(min_length=1)
    preceding_crop_ids: list[str] = Field(min_length=1)
    decision_at: datetime
    target_available_at: datetime
    outcome_id: str = Field(min_length=1)
    feature_observation_ids: list[str] = Field(min_length=1)
    split: str


def check_decision_features(decision_at, features):
    """Reject unknown availability, future realized observations and unvalidated features."""
    blockers = []
    if decision_at is None or decision_at.tzinfo is None:
        return ["missing_or_unzoned_decision_timestamp"]
    for feature in features:
        identifier = feature["id"]
        available = feature.get("available_at")
        end = feature.get("support_end")
        if feature.get("validation_status") != "accepted":
            blockers.append(f"{identifier}:unvalidated")
        if available is None or available.tzinfo is None or available > decision_at:
            blockers.append(f"{identifier}:not_available_at_decision")
        if end is None or end.tzinfo is None or end > decision_at:
            blockers.append(f"{identifier}:future_or_unknown_support")
    return blockers


def check_splits(examples):
    groups, identities, blockers = {}, set(), []
    partitions = {"train": [], "validation": [], "test": []}
    for raw in examples:
        example = DecisionExample.model_validate(raw)
        if example.split not in partitions:
            blockers.append(f"{example.example_id}:invalid_split")
            continue
        if example.context_id in identities:
            blockers.append(f"{example.example_id}:duplicate_context")
        identities.add(example.context_id)
        if example.group_id in groups and groups[example.group_id] != example.split:
            blockers.append(f"{example.example_id}:group_crosses_splits")
        groups[example.group_id] = example.split
        if example.decision_at.tzinfo is None or example.target_available_at.tzinfo is None:
            blockers.append(f"{example.example_id}:missing_timezone")
        else:
            partitions[example.split].append(example)
    for name, partition in partitions.items():
        if not partition:
            blockers.append(f"{name}:no_eligible_examples")
    for earlier, later in (("train", "validation"), ("train", "test"), ("validation", "test")):
        if partitions[earlier] and partitions[later]:
            if max(row.target_available_at for row in partitions[earlier]) >= min(
                row.decision_at for row in partitions[later]
            ):
                blockers.append(f"{earlier}/{later}:temporal_leakage")
    return blockers


def _write_table(output, name, records, columns):
    frame = pd.DataFrame(records, columns=columns)
    frame.to_parquet(output / name, index=False)
    restored = pd.read_parquet(output / name)
    if len(restored) != len(frame) or list(restored.columns) != columns:
        raise ValueError(f"{name}: export count/schema mismatch")
    # JSON serialization avoids numpy array equality ambiguity for nested columns.
    if restored.to_json(orient="records", double_precision=15) != frame.to_json(orient="records", double_precision=15):
        raise ValueError(f"{name}: export values differ")


def export_preparation(store, config_path: Path, output: Path, repository: Path):
    output.mkdir(parents=True, exist_ok=False)
    try:
        return _export_preparation(store, config_path, output, repository)
    except Exception as error:
        (output / "failure.json").write_text(json.dumps({
            "training_ready": False, "status": "failed", "error_type": type(error).__name__,
        }), encoding="utf-8")
        raise


def _export_preparation(store, config_path, output, repository):
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    if config.get("schema_version") != "1" or config.get("task_id") != "following_crop_yield_v1":
        raise ValueError("Unreviewed dataset contract")
    started = datetime.now(timezone.utc).isoformat()
    with store.session(repeatable_read=True) as connection:
        # Every partition comes from the same committed database snapshot.
        outcomes = connection.execute(
            "SELECT p.outcome_id,p.context_id,p.trial_id,t.site_id,p.crop_id,p.cultivar_id,"
            "p.harvest_year,p.plot_id,p.main_plot_id,p.rotation_code,p.sowing_date,p.harvest_date,"
            "p.yield_kg_ha,p.mass_basis,p.availability,p.validation_status,p.source_asset_id,"
            "p.source_record_locator,p.record_context "
            "FROM crop_performance p JOIN crop_trials t USING(trial_id) ORDER BY p.outcome_id"
        ).fetchall()
        weather = connection.execute(
            "SELECT canonical_observation_id,context_id,field_id,variable_id,scientific_record,validation_status "
            "FROM canonical_observations ORDER BY canonical_observation_id"
        ).fetchall()
        evidence = connection.execute(
            "SELECT e.canonical_observation_id,e.observation_id,a.extraction_job_id,"
            "a.acquired_record->>'raw_sha256',a.acquired_record->>'retrieved_at',e.source_record_locator "
            "FROM observation_evidence e JOIN acquisition_observations a USING(observation_id) "
            "ORDER BY e.canonical_observation_id,e.observation_id,a.extraction_job_id"
        ).fetchall()
        aliases = connection.execute(
            "SELECT alias_field_id,canonical_field_id,evidence FROM field_aliases ORDER BY alias_field_id"
        ).fetchall()
        resources = connection.execute(
            "SELECT source_asset_id,resource_name,schema_definition,rows FROM trial_resources "
            "ORDER BY source_asset_id,resource_name"
        ).fetchall()
        assets = connection.execute(
            "SELECT source_asset_id,path,raw_sha256,origin FROM source_assets ORDER BY source_asset_id"
        ).fetchall()
        unlinked = connection.execute(
            "SELECT count(*) FROM observations o WHERE o.source_id='SRC-004' AND NOT EXISTS "
            "(SELECT 1 FROM observation_evidence e WHERE e.observation_id=o.observation_id)"
        ).fetchone()[0]
        if unlinked:
            raise ValueError("Unreconciled weather evidence; run reconcile-data before exporting")
    examples, targets, features, splits, lineage, exclusions = [], [], [], [], [], []
    for row in outcomes:
        (outcome, context, trial, site, crop, cultivar, year, plot, main_plot, rotation, sowing,
         harvest, value, basis, availability, validation, asset, locator, metadata) = row
        example = fingerprint([config["task_id"], context, outcome])
        # There is no actual decision timestamp or reviewed preceding sequence yet.
        # Do not turn sowing dates or rotation labels into invented answers.
        examples.append({
            "example_id": example, "context_id": context, "site_id": site, "trial_id": trial,
            "group_id": fingerprint([site, trial, metadata["block"], main_plot]),
            "plot_id": plot, "crop_id": crop, "cultivar_id": cultivar, "harvest_year": year,
            "rotation_code": rotation, "decision_at": metadata.get("decision_at"),
            "preceding_crop_ids_json": json.dumps(metadata.get("previous_crop_sequence")),
            "sowing_date": sowing.isoformat() if sowing else None,
            "harvest_date": harvest.isoformat() if harvest else None,
        })
        targets.append({
            "example_id": example, "outcome_id": outcome, "variable_id": "grain_yield",
            "value": value, "unit": "kg/ha", "mass_basis": basis, "availability": availability,
            "validation_status": validation, "source_asset_id": asset, "source_record_locator": locator,
            "target_available_at": None, "validation_evidence": None,
        })
        reasons = ["decision_timestamp_not_documented", "preceding_sequence_not_reviewed",
                   "no_validated_decision_time_environment_join"]
        if validation != "accepted":
            reasons.append("target_pending_validation")
        if value is None:
            reasons.append("source_yield_missing")
        if availability == "requires_review":
            reasons.append("source_notes_or_identity_need_review")
        exclusions.append({"example_id": example, "reasons": reasons})
        splits.append({"example_id": example, "split": "withheld", "reason": ";".join(reasons)})
        lineage.append({"record_id": outcome, "record_kind": "target", "source_record_id": outcome,
                        "acquisition_id": None, "raw_sha256": asset, "retrieved_at": None, "locator": locator})
        # Only original context is exported here. It is not silently approved as a predictor.
        for name, value_text in (("rotation_code", rotation), ("cultivar_id", cultivar)):
            features.append({"example_id": example, "feature_id": name, "value_text": value_text,
                             "available_at": None, "support_end": None, "validation_status": "pending",
                             "eligible": False, "source_record_id": outcome})
    weather_records = [
        {"canonical_observation_id": identifier, "context_id": context, "field_id": field,
         "variable_id": variable, "validation_status": status, "scientific_record_json": json.dumps(record, sort_keys=True)}
        for identifier, context, field, variable, record, status in weather
    ]
    lineage.extend(
        {"record_id": canonical, "record_kind": "weather", "source_record_id": observation,
         "acquisition_id": job, "raw_sha256": digest, "retrieved_at": retrieved, "locator": locator}
        for canonical, observation, job, digest, retrieved, locator in evidence
    )
    minimum = config["minimum_readiness"]
    site_count = len({row["site_id"] for row in examples})
    year_count = len({row["harvest_year"] for row in examples})
    rotation_count = len({row["rotation_code"] for row in examples})
    blockers = [
        "No reviewed decision-time example/feature bindings; all candidates are withheld.",
        "Independent target and scientific feature validation remains incomplete.",
        "Sample-size/power review and leakage-safe split assignment remain required.",
        "Dutch reference weather cannot be joined to the UK trial site.",
    ]
    if site_count < minimum["distinct_sites"]:
        blockers.append("Insufficient independent sites for the declared generalization scope.")
    if year_count < minimum["distinct_harvest_years"]:
        blockers.append("Insufficient harvest-year coverage.")
    if rotation_count < minimum["distinct_rotation_treatments"]:
        blockers.append("Insufficient distinct rotation treatments.")
    _write_table(output, "examples.parquet", examples, [
        "example_id", "context_id", "site_id", "trial_id", "group_id", "plot_id", "crop_id",
        "cultivar_id", "harvest_year", "rotation_code", "decision_at", "preceding_crop_ids_json",
        "sowing_date", "harvest_date"])
    _write_table(output, "features.parquet", features, [
        "example_id", "feature_id", "value_text", "available_at", "support_end", "validation_status",
        "eligible", "source_record_id"])
    _write_table(output, "targets.parquet", targets, [
        "example_id", "outcome_id", "variable_id", "value", "unit", "mass_basis", "availability",
        "validation_status", "source_asset_id", "source_record_locator", "target_available_at", "validation_evidence"])
    _write_table(output, "splits.parquet", splits, ["example_id", "split", "reason"])
    _write_table(output, "lineage.parquet", lineage, [
        "record_id", "record_kind", "source_record_id", "acquisition_id", "raw_sha256", "retrieved_at", "locator"])
    _write_table(output, "weather.parquet", weather_records, [
        "canonical_observation_id", "context_id", "field_id", "variable_id", "validation_status", "scientific_record_json"])
    # Preserve factor definitions and notes once, rather than repeat them for every outcome.
    (output / "trial_resources.json").write_text(json.dumps([
        {"source_asset_id": asset, "name": name, "schema": schema, "rows": rows}
        for asset, name, schema, rows in resources
    ], indent=2), encoding="utf-8")
    (output / "field_aliases.json").write_text(json.dumps([
        {"alias": alias, "canonical": canonical, "evidence": evidence}
        for alias, canonical, evidence in aliases
    ], indent=2), encoding="utf-8")
    with (output / "exclusions.jsonl").open("w", encoding="utf-8") as stream:
        for item in exclusions:
            stream.write(json.dumps(item) + "\n")
    verified_assets = []
    for identifier, path, digest, origin in assets:
        if sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError("Snapshot source asset checksum mismatch")
        verified_assets.append({"source_asset_id": identifier, "path": path, "sha256": digest, "origin": origin})
    (output / "assets.json").write_text(json.dumps(verified_assets, indent=2), encoding="utf-8")
    report = {
        "training_ready": False, "status": "blocked", "full_plan_complete": False,
        "candidate_examples": len(examples), "eligible_examples": 0,
        "independent_sites": site_count, "harvest_years": year_count, "rotation_codes": rotation_count,
        "canonical_weather_observations": len(weather), "blockers": blockers,
        "attribution": ATTRIBUTION, "acknowledgement": ACKNOWLEDGEMENT, "citation": CITATION,
    }
    (output / "readiness.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "contract.yaml").write_bytes(config_bytes)
    (output / "decision_example.schema.json").write_text(
        json.dumps(DecisionExample.model_json_schema(), indent=2), encoding="utf-8")
    files = [{"path": path.name, "sha256": sha256(path.read_bytes()).hexdigest(),
              "row_count": len(pd.read_parquet(path)) if path.suffix == ".parquet" else None}
             for path in sorted(output.iterdir())]
    manifest = {
        "kind": "ml_dataset_preparation", "training_ready": False, "status": "blocked",
        "schema_version": "1", "task_id": config["task_id"], "files": files,
        "snapshot_id": fingerprint({"config": sha256(config_bytes).hexdigest(), "files": files}),
        "config_sha256": sha256(config_bytes).hexdigest(),
        "code": {str(p.relative_to(repository)): sha256(p.read_bytes()).hexdigest()
                 for p in sorted((repository / "src").rglob("*")) if p.suffix in (".py", ".sql")},
        "lock_sha256": sha256((repository / "uv.lock").read_bytes()).hexdigest(),
        "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
        "attribution": ATTRIBUTION, "acknowledgement": ACKNOWLEDGEMENT, "citation": CITATION,
    }
    pending = output / "manifest.pending"
    pending.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pending.replace(output / "manifest.json")
    return report


def load_training_snapshot(path):
    manifest = json.loads((path / "manifest.json").read_bytes())
    if manifest.get("training_ready") is not True or manifest.get("status") != "ready":
        raise ValueError("This is a preparation snapshot, not an approved training dataset")
    for item in manifest["files"]:
        target = (path / item["path"]).resolve()
        if not target.is_relative_to(path.resolve()):
            raise ValueError("Manifest file escapes snapshot directory")
        if sha256(target.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Training snapshot checksum mismatch")
    tables = {name: pd.read_parquet(path / f"{name}.parquet")
              for name in ("examples", "features", "targets", "splits", "lineage")}
    examples = tables["examples"]
    if examples.empty:
        raise ValueError("No training examples")
    for name in ("examples", "targets", "splits"):
        if tables[name]["example_id"].duplicated().any():
            raise ValueError(f"{name}: duplicate example IDs")
    ids = set(examples["example_id"])
    if any(set(tables[name]["example_id"]) != ids for name in ("targets", "features", "splits")):
        raise ValueError("Example, feature, target and split coverage differs")
    targets = tables["targets"].set_index("example_id")
    splits = tables["splits"].set_index("example_id")
    assignments = []
    for raw in examples.to_dict("records"):
        identifier = raw["example_id"]
        target = targets.loc[identifier]
        if target["validation_status"] != "accepted" or not target["validation_evidence"]:
            raise ValueError("Unvalidated target")
        if pd.isna(target["value"]) or target["unit"] != "kg/ha":
            raise ValueError("Missing or incompatible target")
        decision = datetime.fromisoformat(raw["decision_at"])
        features = tables["features"].loc[tables["features"]["example_id"] == identifier]
        checks = check_decision_features(decision, [
            {"id": row.feature_id, "validation_status": row.validation_status,
             "available_at": datetime.fromisoformat(row.available_at) if row.available_at else None,
             "support_end": datetime.fromisoformat(row.support_end) if row.support_end else None}
            for row in features.itertuples()
        ])
        if checks or not features["eligible"].all():
            raise ValueError(f"Unsafe features: {checks}")
        assignments.append({
            "example_id": identifier, "site_id": raw["site_id"], "trial_id": raw["trial_id"],
            "group_id": raw["group_id"], "context_id": raw["context_id"], "crop_id": raw["crop_id"],
            "preceding_crop_ids": json.loads(raw["preceding_crop_ids_json"]),
            "decision_at": decision, "target_available_at": target["target_available_at"],
            "outcome_id": target["outcome_id"], "feature_observation_ids": list(features["source_record_id"]),
            "split": splits.loc[identifier, "split"],
        })
    blockers = check_splits(assignments)
    if blockers:
        raise ValueError(f"Unsafe splits: {blockers}")
    return tables
