"""End-to-end KML-to-profile orchestration."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
import json

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


def run_pipeline(kml_path: str | Path, project_name: Optional[str] = None,
                 domains: Optional[Iterable[str]] = None,
                 persist: bool = True) -> Dict[str, Any]:
    fields = calculate_centroids(calculate_area_and_perimeter(load_kml(kml_path)))
    export_paths = export_fields_spatial(fields, settings.processed_dir / "fields")
    init_db() if persist else None
    profiles: Dict[str, Any] = {}
    acquired_by_field: Dict[str, Any] = {}

    if persist:
        with get_db_session() as session:
            project = Project(name=project_name or settings.project_cfg.get("project", {}).get("name", "AgriData"),
                              region=settings.project_cfg.get("project", {}).get("region", "Unknown"))
            session.add(project)
            session.flush()
            for _, row in fields.iterrows():
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
        acquired = acquire_field_data(row, domains=domains)
        profile = extract_field_profile(row, acquired)
        profiles[row.field_id] = profile
        acquired_by_field[row.field_id] = acquired
        export_agricultural_profile(row.field_id, profile)
        for result in acquired.values():
            raw_file = result.get("raw_file")
            if raw_file and Path(raw_file).exists() and persist:
                with get_db_session() as session:
                    register_source_asset(session, Path(raw_file), Path(raw_file).suffix.lstrip(".") or "json")
        if persist:
            with get_db_session() as session:
                record_batch_observations(session, flatten_observations(row.field_id, acquired))

    report_path = write_project_report(profiles.values())
    return {"fields": fields, "profiles": profiles, "acquired": acquired_by_field,
            "exports": export_paths, "project_report": report_path}
