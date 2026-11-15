"""End-to-end KML-to-profile orchestration."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import json
import hashlib
import uuid
import pandas as pd

from agri_data.config import settings
from agri_data.geo.kml import load_kml
from agri_data.geo.area import calculate_area_and_perimeter
from agri_data.geo.geometry import calculate_centroids
from agri_data.storage.database import init_db, get_db_session
from agri_data.storage.models import Field, ExtractionJob, Project
from agri_data.storage.observations import record_batch_observations
from agri_data.storage.assets import register_source_asset
from agri_data.storage.exports import export_fields_spatial, export_agricultural_profile
from .acquisition import acquire_field_data
from .extraction import extract_field_profile, flatten_observations
from agri_data.reporting import write_project_report
from agri_data.storage.full_output import write_bundle


def run_pipeline(kml_path: str | Path, project_name: Optional[str] = None,
                 domains: Optional[Iterable[str]] = None,
                 persist: bool = True, mode: str = "live",
                 start_date: str = "2025-01-01", end_date: str = "2025-12-31") -> Dict[str, Any]:
    if mode not in {"live", "demo"}:
        raise ValueError("mode must be live or demo")
    if pd.Timestamp(start_date) > pd.Timestamp(end_date):
        raise ValueError("start_date must precede end_date")
    domains = list(domains) if domains is not None else None
    input_bytes = Path(kml_path).read_bytes()
    checksum = hashlib.sha256(input_bytes).hexdigest()
    raw_input = settings.raw_dir / "inputs" / (checksum + Path(kml_path).suffix.lower())
    raw_input.parent.mkdir(parents=True, exist_ok=True)
    if not raw_input.exists():
        raw_input.write_bytes(input_bytes)
    run_id = uuid.uuid4().hex
    output_dir = settings.exports_dir / run_id
    output_dir.mkdir(parents=True)
    fields = calculate_centroids(calculate_area_and_perimeter(load_kml(kml_path)))
    fields["field_id"] = ["FIELD_" + hashlib.sha256(((project_name or "default") + geom.normalize().wkb_hex).encode()).hexdigest()[:24] for geom in fields.geometry]
    fields = fields.drop_duplicates("field_id")
    export_paths = export_fields_spatial(fields, output_dir / "fields")
    init_db() if persist else None
    profiles: Dict[str, Any] = {}
    acquired_by_field: Dict[str, Any] = {}

    if persist:
        with get_db_session() as session:
            register_source_asset(session, raw_input, raw_input.suffix.lstrip("."))
            project_label = project_name or settings.project_cfg.get("project", {}).get("name", "AgriData")
            project = session.query(Project).filter_by(name=project_label).first()
            if project is None:
                project = Project(name=project_label,
                              region=settings.project_cfg.get("project", {}).get("region", "Unknown"))
            session.add(project)
            session.flush()
            for _, row in fields.iterrows():
                if session.query(Field).filter_by(field_id=row.field_id).first():
                    continue
                metadata = row.get("extended_data")
                if isinstance(metadata, str):
                    try: metadata = json.loads(metadata)
                    except json.JSONDecodeError: metadata = {"raw": metadata}
                session.add(Field(field_id=row.field_id, project_id=project.id, name=row.get("name", row.field_id),
                                  description=row.get("description"), folder=row.get("folder", "Default"),
                                  geometry_wkt=row.geometry.wkt, centroid_lon=row.get("centroid_lon"),
                                  centroid_lat=row.get("centroid_lat"), rep_lon=row.get("rep_lon"), rep_lat=row.get("rep_lat"),
                                  area_ha=row.get("area_ha"), area_sqm=row.get("area_sqm"),
                                  perimeter_m=row.get("perimeter_m"), utm_crs=row.get("utm_crs"), metadata_json=metadata or {}))
            session.flush()

    for _, row in fields.iterrows():
        acquired = acquire_field_data(row, domains=domains, start_date=start_date, end_date=end_date, mode=mode)
        profile = extract_field_profile(row, acquired)
        profile["sources"] = {domain: {key: value for key, value in result.items() if key in {"status", "reason", "mode", "raw_file", "valid"}} for domain, result in acquired.items()}
        profiles[row.field_id] = profile
        acquired_by_field[row.field_id] = acquired
        for result in acquired.values():
            raw_file = result.get("raw_file")
            if raw_file and Path(raw_file).exists() and persist:
                with get_db_session() as session:
                    asset = register_source_asset(session, Path(raw_file), Path(raw_file).suffix.lstrip(".") or "json")
                    key = hashlib.sha256((row.field_id + str(asset.id) + mode + "processing-v2").encode()).hexdigest()
                    if not session.query(ExtractionJob).filter_by(job_id=key).first():
                        observations = flatten_observations(row.field_id, {"result": result})
                        for observation in observations:
                            observation["source_asset_id"] = asset.id
                        record_batch_observations(session, observations)
                        session.add(ExtractionJob(job_id=key, source_id=result["source_id"], field_ids_json=[row.field_id], status="COMPLETED", completed_at=datetime.utcnow()))
        observations = flatten_observations(row.field_id, acquired)
        bundle_dir = output_dir / "full" / row.field_id
        manifest = write_bundle(observations, bundle_dir, {"mode": mode, "sources": profile["sources"]})
        profile["complete_observations"] = {"path": str(bundle_dir / "observations.jsonl"), **manifest}
        export_agricultural_profile(row.field_id, profile, output_dir / row.field_id)
        (output_dir / row.field_id / "observations.json").write_text(json.dumps(observations, indent=2, default=str))
        if observations:
            pd.DataFrame(observations).to_parquet(output_dir / row.field_id / "observations.parquet", index=False)

    report_path = write_project_report(profiles.values(), output_dir / "project_summary.json")
    (output_dir / "manifest.json").write_text(json.dumps({"run_id": run_id, "kml_checksum": checksum, "input_asset": str(raw_input), "mode": mode, "domains": domains, "start_date": start_date, "end_date": end_date, "processing_version": "2", "profiles": list(profiles)}, indent=2))
    return {"fields": fields, "profiles": profiles, "acquired": acquired_by_field,
            "exports": export_paths, "project_report": report_path}
