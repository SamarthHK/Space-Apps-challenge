"""
Crop development, growth progression, and thermal time modeling.
Tracks phenological stages (germination, vegetative, flowering, grain filling, maturity)
and simulates LAI growth curves and dry biomass accumulation.
"""

from typing import Dict, Any, List
import math
import numpy as np
from agri_data.config import settings


def simulate_growth_stages_and_lai(
    crop_name: str,
    sowing_day_of_year: int = 160  # e.g. June 9th (onset of Kharif monsoon)
) -> Dict[str, Any]:
    """
    Simulates stage progression, thermal requirements, and LAI development trajectory for a crop.
    """
    crop_cfg = settings.get_crop(crop_name)
    if not crop_cfg:
        raise ValueError(f"Crop '{crop_name}' not found")

    stages = crop_cfg.get("stages", {})
    cumulative_days = 0
    stage_schedule = []

    for s_name, s_info in stages.items():
        dur_range = s_info.get("duration_days", [20, 30])
        dur = int((dur_range[0] + dur_range[1]) / 2)
        start_doy = sowing_day_of_year + cumulative_days
        end_doy = start_doy + dur
        stage_schedule.append({
            "stage": s_name,
            "duration_days": dur,
            "start_day_of_year": start_doy,
            "end_day_of_year": end_doy,
            "base_temperature_c": s_info.get("base_temp", 10.0)
        })
        cumulative_days += dur

    # Generate sigmoid LAI curve over growing season
    total_duration = cumulative_days
    timeline = []
    max_lai = 4.8 if crop_name in ["sugarcane", "maize"] else 3.2

    for d in range(0, total_duration + 1, 10):
        # Logistic growth up to flowering (~60% of duration), then senescence
        rel_time = d / total_duration
        if rel_time <= 0.65:
            # Sigmoid growth
            lai = max_lai / (1.0 + math.exp(-12.0 * (rel_time - 0.35)))
        else:
            # Senescence phase
            peak_lai = max_lai
            senescence_rate = (rel_time - 0.65) / 0.35
            lai = max(0.2, peak_lai * (1.0 - 0.8 * senescence_rate))

        timeline.append({
            "days_after_sowing": d,
            "day_of_year": sowing_day_of_year + d,
            "simulated_lai": round(float(lai), 2)
        })

    return {
        "crop": crop_cfg.get("common_name", crop_name),
        "total_lifecycle_days": total_duration,
        "stages": stage_schedule,
        "lai_development_curve": timeline
    }
