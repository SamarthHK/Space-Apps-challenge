"""Human- and machine-readable project reporting."""

from pathlib import Path
from typing import Any, Dict, Iterable
import json

from agri_data.config import settings


def summarize_field_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    climate = profile.get("climate", {})
    soil = profile.get("soil", {})
    land = profile.get("historical_land", {})
    return {
        "field_id": profile.get("field_id"),
        "area_ha": profile.get("field", {}).get("area_ha"),
        "soil_texture": soil.get("texture_class"),
        "soil_ph": soil.get("soil_ph"),
        "annual_rainfall_mm": climate.get("total_rainfall_mm"),
        "annual_reference_et0_mm": climate.get("drought", {}).get("annual_reference_et0_mm"),
        "longest_dry_spell_days": climate.get("drought", {}).get("dry_spells", {}).get("longest_dry_spell_days"),
        "peak_ndvi": land.get("peak_ndvi"),
    }


def build_project_report(profiles: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    summaries = [summarize_field_profile(profile) for profile in profiles]
    return {
        "project": settings.project_cfg.get("project", {}),
        "field_count": len(summaries),
        "fields": summaries,
        "limitations": [
            "Synthetic fallbacks are used when external APIs are unavailable.",
            "SoilGrids does not provide laboratory EC or available NPK values.",
            "Suitability and rotation outputs are agronomic indicators, not economic forecasts.",
        ],
    }


def write_project_report(profiles: Iterable[Dict[str, Any]], output_path: str | Path | None = None) -> Path:
    path = Path(output_path or settings.exports_dir / "project_summary.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    report = build_project_report(profiles)
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path
