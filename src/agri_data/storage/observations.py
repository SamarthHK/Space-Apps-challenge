"""
Observation persistence and querying utilities.
Inserts standardized observations into the master observation table with full provenance.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from .models import Observation, Field, Variable, DataSource, SourceAsset
from agri_data.config import settings


def record_observation(
    session: Session,
    field_code: str,
    variable_code: str,
    value_numeric: Optional[float],
    measurement_type: str,
    source_code: Optional[str] = None,
    source_asset_id: Optional[int] = None,
    observed_at: Optional[datetime] = None,
    depth_top_cm: Optional[float] = None,
    depth_bottom_cm: Optional[float] = None,
    statistic: str = "mean",
    spatial_resolution_m: Optional[float] = None,
    spatial_coverage_percent: Optional[float] = None,
    original_value: Optional[float] = None,
    original_unit: Optional[str] = None,
    standardized_unit: Optional[str] = None,
    quality_flag: str = "VALID",
    value_text: Optional[str] = None
) -> Observation:
    """Records a single observation in the master observations table."""
    field = session.query(Field).filter_by(field_id=field_code).first()
    if not field:
        raise ValueError(f"Field not found in database: {field_code}")

    var = session.query(Variable).filter_by(variable_id=variable_code).first()
    if not var:
        raise ValueError(f"Variable not recognized: {variable_code}")

    source = None
    if source_code:
        source = session.query(DataSource).filter_by(source_id=source_code).first()
        if source is None:
            configured = settings.get_source(source_code)
            configured_id = configured.get("id") if configured else None
            if configured_id:
                source = session.query(DataSource).filter_by(source_id=configured_id).first()

    obs = Observation(
        field_id=field.id,
        variable_id=var.id,
        source_id=source.id if source else None,
        source_asset_id=source_asset_id,
        value_numeric=value_numeric,
        value_text=value_text,
        original_value=original_value if original_value is not None else value_numeric,
        original_unit=original_unit or var.canonical_unit,
        standardized_unit=standardized_unit or var.canonical_unit,
        observed_at=observed_at,
        depth_top_cm=depth_top_cm,
        depth_bottom_cm=depth_bottom_cm,
        statistic=statistic,
        measurement_type=measurement_type,
        spatial_resolution_m=spatial_resolution_m,
        spatial_coverage_percent=spatial_coverage_percent,
        quality_flag=quality_flag
    )
    session.add(obs)
    return obs


def record_batch_observations(
    session: Session,
    observations_list: List[Dict[str, Any]]
) -> int:
    """Bulk records a list of observation dictionaries."""
    count = 0
    for obs_data in observations_list:
        record_observation(
            session=session,
            field_code=obs_data["field_id"],
            variable_code=obs_data["variable_id"],
            value_numeric=obs_data.get("value_numeric"),
            value_text=obs_data.get("value_text"),
            measurement_type=obs_data.get("measurement_type", "modelled"),
            source_code=obs_data.get("source_id"),
            source_asset_id=obs_data.get("source_asset_id"),
            observed_at=obs_data.get("observed_at"),
            depth_top_cm=obs_data.get("depth_top_cm"),
            depth_bottom_cm=obs_data.get("depth_bottom_cm"),
            statistic=obs_data.get("statistic", "mean"),
            spatial_resolution_m=obs_data.get("spatial_resolution_m"),
            spatial_coverage_percent=obs_data.get("spatial_coverage_percent"),
            original_value=obs_data.get("original_value"),
            original_unit=obs_data.get("original_unit"),
            standardized_unit=obs_data.get("standardized_unit"),
            quality_flag=obs_data.get("quality_flag", "VALID")
        )
        count += 1
    session.flush()
    return count


def get_field_observations(
    session: Session,
    field_code: str,
    category: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves all observations for a specific field, optionally filtered by category."""
    query = (
        session.query(Observation, Variable, DataSource)
        .join(Field, Observation.field_id == Field.id)
        .join(Variable, Observation.variable_id == Variable.id)
        .outerjoin(DataSource, Observation.source_id == DataSource.id)
        .filter(Field.field_id == field_code)
    )
    if category:
        query = query.filter(Variable.category == category)

    results = []
    for obs, var, src in query.all():
        results.append({
            "observation_id": obs.id,
            "field_id": field_code,
            "variable_id": var.variable_id,
            "category": var.category,
            "value": obs.value_numeric,
            "unit": obs.standardized_unit,
            "depth_top_cm": obs.depth_top_cm,
            "depth_bottom_cm": obs.depth_bottom_cm,
            "observed_at": obs.observed_at.isoformat() if obs.observed_at else None,
            "source": src.name if src else "Unknown",
            "source_id": src.source_id if src else None,
            "measurement_type": obs.measurement_type,
            "statistic": obs.statistic,
            "spatial_resolution_m": obs.spatial_resolution_m,
            "quality_flag": obs.quality_flag
        })
    return results
