"""Explicit tabular imports with preserved source bytes and no fabricated values."""
import csv
import hashlib
import json
import math
from pathlib import Path
from datetime import datetime
from agri_data.config import settings

DOMAINS = {"soil", "terrain", "rainfall", "climate", "water", "historical_land",
           "crop_requirements", "germination", "crop_development", "crop_performance",
           "biological_environment", "rotation", "management", "sensors", "environmental_quality"}


def load_import_plan(path):
    path = Path(path).resolve()
    plan = json.loads(path.read_text(encoding="utf-8"))
    datasets = plan.get("datasets", [])
    names = set()
    for dataset in datasets:
        for key in ("id", "source_id", "domain", "path", "variables", "field_name"):
            if key not in dataset:
                raise ValueError(f"Import dataset missing {key}")
        if dataset["id"] in names:
            raise ValueError("Duplicate import dataset id")
        names.add(dataset["id"])
        if dataset["domain"] not in DOMAINS:
            raise ValueError(f"Unknown domain: {dataset['domain']}")
        dataset["path"] = str((path.parent / dataset["path"]).resolve())
        if not Path(dataset["path"]).is_file():
            raise FileNotFoundError(dataset["path"])
        for name, definition in dataset["variables"].items():
            if not definition.get("unit") or not definition.get("description"):
                raise ValueError(f"Variable {name} requires unit and description")
            existing = settings.get_variable(name)
            if existing and existing["canonical_unit"] != definition["unit"]:
                raise ValueError(f"Unit mismatch for {name}; explicitly convert before import")
    return datasets


def import_dataset(dataset, field):
    """Load an explicitly field-associated long-format CSV or JSON observation list."""
    path = Path(dataset["path"])
    payload = path.read_bytes()
    target = settings.raw_dir / "imports" / (hashlib.sha256(payload).hexdigest() + path.suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(payload)
    if path.suffix.lower() == ".csv":
        records = list(csv.DictReader(payload.decode("utf-8-sig").splitlines()))
    elif path.suffix.lower() == ".json":
        records = json.loads(payload)
    else:
        raise ValueError("Import supports CSV and JSON")
    if not isinstance(records, list):
        raise ValueError("JSON import must be an observation array")
    observations = []
    for number, original in enumerate(records, 1):
        row = dict(original)
        variable = row.get("variable_id")
        if variable not in dataset["variables"]:
            raise ValueError(f"Row {number}: undeclared variable {variable}")
        value = row.get("value_numeric")
        if value not in (None, ""):
            value = float(value)
            if not math.isfinite(value):
                raise ValueError(f"Row {number}: non-finite numeric value")
        else:
            value = None
        if value is None and not row.get("value_text") and not row.get("missing_reason"):
            raise ValueError(f"Row {number}: missing value requires missing_reason")
        timestamp = row.get("observed_at")
        if timestamp:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        row.update(value_numeric=value, observed_at=timestamp, field_id=field.field_id,
                   source_id=dataset["source_id"], domain=dataset["domain"],
                   standardized_unit=dataset["variables"][variable]["unit"],
                   measurement_type=dataset.get("measurement_type", "measured"),
                   quality_flag="MISSING" if value is None and not row.get("value_text") else row.get("quality_flag", "VALID"),
                   import_row=number, original_record=original)
        for key in ("depth_top_cm", "depth_bottom_cm"):
            row[key] = float(row[key]) if row.get(key) not in (None, "") else None
        if row["depth_top_cm"] is not None and row["depth_bottom_cm"] is not None and row["depth_top_cm"] >= row["depth_bottom_cm"]:
            raise ValueError(f"Row {number}: invalid depth interval")
        observations.append(row)
    return {"source_id": dataset["source_id"], "domain": dataset["domain"],
            "dataset_name": dataset["id"], "raw_file": str(target), "mode": "import",
            "status": "available", "observations": observations, "valid": True}
