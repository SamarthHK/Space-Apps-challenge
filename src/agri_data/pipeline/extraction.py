"""Convert acquired source results into field profiles and database-ready rows."""

from typing import Any, Dict, List
import pandas as pd

from agri_data.processing.climate import aggregate_climate_metrics
from agri_data.processing.drought import calculate_comprehensive_drought_indicators
from agri_data.processing.vegetation import extract_phenology_metrics
from agri_data.processing.soil import process_soil_profile


def extract_field_profile(field: Any, acquired: Dict[str, Any]) -> Dict[str, Any]:
    profile: Dict[str, Any] = {"field_id": field.field_id, "field": {}, "soil": {},
                               "climate": {}, "water": {}, "historical_land": {}}
    soil = acquired.get("soil", {})
    soil_obs = soil.get("observations", [])
    if soil_obs:
        profile["soil"] = process_soil_profile(soil_obs)
        # Keep the canonical shallow pH readily available for crop scoring.
        for obs in soil_obs:
            if obs.get("variable_id") == "soil_ph" and obs.get("depth_top_cm", 999) == 0:
                profile["soil"]["soil_ph"] = obs.get("value_numeric")
                break

    climate = acquired.get("climate", {})
    daily = climate.get("daily_df")
    if isinstance(daily, pd.DataFrame) and not daily.empty:
        profile["climate"] = aggregate_climate_metrics(daily)
        profile["climate"]["drought"] = calculate_comprehensive_drought_indicators(daily)
        # Suitability functions historically consume these top-level keys.
        profile["total_rainfall_mm"] = profile["climate"].get("total_rainfall_mm")
        profile["temperature"] = profile["climate"].get("temperature", {})

    land = acquired.get("historical_land", {})
    scenes = land.get("scenes_df")
    if isinstance(scenes, pd.DataFrame) and not scenes.empty:
        profile["historical_land"] = extract_phenology_metrics(scenes)
    profile["field"] = {k: field.get(k) for k in ("name", "area_ha", "area_sqm", "perimeter_m", "centroid_lon", "centroid_lat") if k in field}
    return profile


def flatten_observations(field_id: str, acquired: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for domain, result in acquired.items():
        for observation in result.get("observations", []):
            row = dict(observation)
            row["field_id"] = field_id
            row.setdefault("domain", result.get("domain", domain))
            rows.append(row)
    return rows
