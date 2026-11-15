"""
Crop performance, historical yields, and cultivation management tracking.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from agri_data.config import settings


def compare_yield_to_benchmark(
    crop_name: str,
    achieved_yield_kg_ha: float,
    district_benchmark_kg_ha: Optional[float] = None
) -> Dict[str, Any]:
    """
    Compares plot yield against district and state agricultural statistics.
    Calculates Yield Gap percentage.
    """
    # Fetch default benchmarks if not passed
    defaults = {
        "sugarcane": 98500.0,
        "ragi": 2350.0,
        "pigeonpea": 1150.0,
        "groundnut": 1680.0,
        "maize": 4450.0
    }
    bench = district_benchmark_kg_ha or defaults.get(crop_name.lower(), 2500.0)
    delta_pct = round(((achieved_yield_kg_ha - bench) / bench) * 100.0, 1)

    return {
        "crop": crop_name,
        "achieved_yield_kg_ha": round(achieved_yield_kg_ha, 1),
        "district_benchmark_kg_ha": round(bench, 1),
        "yield_delta_pct": delta_pct,
        "performance_class": "Above District Average" if delta_pct >= 0 else "Below Potential"
    }


def structure_cultivation_event(
    event_type: str,
    event_date: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validates and standardizes a farm management event:
    (sowing, irrigation, fertilizer_application, tillage, weed_control, harvest).
    """
    valid_types = {
        "sowing", "irrigation", "fertilizer_application",
        "tillage", "weed_control", "pest_control", "harvest"
    }
    if event_type not in valid_types:
        raise ValueError(f"Invalid management event type: {event_type}")

    return {
        "event_type": event_type,
        "event_date": event_date,
        "details": details,
        "recorded_at": datetime.utcnow().isoformat()
    }
