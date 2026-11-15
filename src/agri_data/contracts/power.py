"""Strict normalization of authentic NASA POWER daily payloads for S01 evidence.

These records remain pending scientific acceptance. No missing value is filled,
no regional sample is represented as a ground measurement, and no crop is inferred.
"""

from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
import json
import math

from .observation import EvidenceType, Observation


PARAMETERS = {
    "PRECTOTCORR": ("daily_rainfall", "F03-003", "mm/day"),
    "T2M": ("temperature_mean", "F04-001", "C"),
    "T2M_MAX": ("temperature_max", "F04-002", "C"),
    "T2M_MIN": ("temperature_min", "F04-003", "C"),
    "RH2M": ("relative_humidity", "F04-005", "%"),
    "WS2M": ("wind_speed", "F04-008", "m/s"),
    "ALLSKY_SFC_SW_DWN": ("solar_radiation", "F04-011", "MJ/m^2/day"),
}


def normalize_power(asset: dict, field_id: str) -> tuple[list[Observation], list[dict], dict]:
    payload = Path(asset["raw_path"]).read_bytes()
    if sha256(payload).hexdigest() != asset["raw_sha256"]:
        raise ValueError("POWER raw asset checksum mismatch")
    raw = json.loads(payload)
    header = raw["header"]
    if header["api"]["name"] != "POWER Daily API":
        raise ValueError("Unexpected provider identity")
    start = datetime.strptime(header["start"], "%Y%m%d")
    end = datetime.strptime(header["end"], "%Y%m%d")
    if end < start:
        raise ValueError("Invalid provider date interval")
    expected = {(start + timedelta(days=i)).strftime("%Y%m%d") for i in range((end - start).days + 1)}
    parameters = raw["properties"]["parameter"]
    for code, (_, _, unit) in PARAMETERS.items():
        if raw["parameters"][code]["units"] != unit:
            raise ValueError(f"Unexpected provider unit for {code}; no guessed conversion allowed")
        if set(parameters[code]) != expected:
            raise ValueError(f"Provider date coverage differs for {code}")
    dataset_id = "NASA_POWER_DAILY_" + header["api"]["version"]
    created = datetime.fromisoformat(asset["retrieved_at"])
    observations, missing = [], []
    for day in sorted(expected):
        for code, (variable, feature_id, unit) in PARAMETERS.items():
            value = parameters[code][day]
            if value == header["fill_value"] or value is None:
                missing.append({
                    "variable_id": variable, "date": day, "availability": "not_available_from_source",
                    "source_record_locator": f"/properties/parameter/{code}/{day}",
                    "reason": "Provider missing-value sentinel; no zero replacement",
                    "source_asset_id": asset["raw_sha256"],
                })
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"Invalid numeric value for {code} at {day}")
            if code in ("PRECTOTCORR", "WS2M") and value < 0:
                raise ValueError(f"Negative {code} at {day}")
            if code == "RH2M" and not 0 <= value <= 100:
                raise ValueError(f"Invalid relative humidity at {day}")
            observation_id = sha256(
                f"{asset['raw_sha256']}|{field_id}|{code}|{day}|power-normalize-1".encode()
            ).hexdigest()
            observations.append(Observation(
                schema_version="1", observation_id=observation_id,
                feature_id=feature_id, variable_id=variable,
                subject_type="field_associated_grid_query", subject_id=field_id, field_id=field_id,
                value_numeric=float(value), original_value=value,
                original_unit=unit, standardized_unit=unit,
                measurement_basis=raw["parameters"][code]["longname"],
                observed_at=datetime.strptime(day, "%Y%m%d"),
                timezone=header["time_standard"], temporal_resolution="daily",
                evidence_type=EvidenceType.reanalysis if code != "ALLSKY_SFC_SW_DWN" else EvidenceType.satellite,
                source_id="SRC-004", dataset_id=dataset_id,
                source_binding_id=f"{dataset_id}:{code}", source_asset_id=asset["raw_sha256"],
                source_record_locator=f"/properties/parameter/{code}/{day}",
                extraction_method="representative_point_query",
                spatial_support="NASA POWER native gridded source product; not a field measurement",
                quality_flags=[], validation_status="pending",
                parent_observation_ids=[], processing_version="power-normalize-1",
                extraction_job_id=asset["request_id"],
                retrieved_at=created, created_at=created, raw_sha256=asset["raw_sha256"],
            ))
        temperature = [parameters[code][day] for code in ("T2M_MIN", "T2M", "T2M_MAX")]
        if all(value is not None and value != header["fill_value"] for value in temperature):
            if not temperature[0] <= temperature[1] <= temperature[2]:
                raise ValueError(f"Inconsistent temperature ordering at {day}")
    metadata = {
        "dataset_id": dataset_id, "header": header, "parameters": raw["parameters"],
        "geometry": raw["geometry"], "record_count": len(observations),
        "expected_daily_values": len(expected) * len(PARAMETERS),
        "missing_count": len(missing), "status": "pending",
        "remaining_checks": [
            "Product-specific spatial resolution and original product versions",
            "Frozen physical thresholds, independent references and all FEAT/CONN contexts",
            "Full source registry and cross-source reference validation",
        ],
    }
    return observations, missing, metadata
