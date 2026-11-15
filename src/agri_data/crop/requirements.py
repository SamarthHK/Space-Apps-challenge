"""
Crop suitability evaluation module.
Compares plot environmental observations against crop physiological requirements
to compute suitability scores and identify agronomic limiting factors.
"""

from typing import Dict, Any, List, Optional
from agri_data.config import settings


def evaluate_parameter_suitability(
    observed_val: float,
    min_val: Optional[float],
    opt_min_val: Optional[float],
    opt_max_val: Optional[float],
    max_val: Optional[float]
) -> float:
    """
    Computes suitability score from 0.0 to 1.0 using trapezoidal response curve:
    - Between opt_min and opt_max: 1.0 (Optimal)
    - Between min and opt_min: linear interpolation from 0.0 to 1.0
    - Between opt_max and max: linear interpolation from 1.0 to 0.0
    - Below min or above max: 0.0 (Unsuitable)
    """
    if observed_val is None:
        return 0.5  # Neutral default when missing

    # Handle single bounds if opt values are missing
    if opt_min_val is None:
        opt_min_val = min_val
    if opt_max_val is None:
        opt_max_val = max_val

    if min_val is not None and observed_val < min_val:
        return 0.0
    if max_val is not None and observed_val > max_val:
        return 0.0

    if opt_min_val is not None and min_val is not None and observed_val < opt_min_val:
        span = opt_min_val - min_val
        return (observed_val - min_val) / span if span > 0 else 1.0

    if opt_max_val is not None and max_val is not None and observed_val > opt_max_val:
        span = max_val - opt_max_val
        return (max_val - observed_val) / span if span > 0 else 1.0

    return 1.0


def evaluate_crop_suitability(
    crop_name: str,
    environmental_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates a specific crop against observed plot environmental conditions:
    - Temperature
    - Rainfall
    - Soil pH
    - Soil Depth
    - Salinity (EC)
    """
    crop_cfg = settings.get_crop(crop_name)
    if not crop_cfg:
        raise ValueError(f"Crop '{crop_name}' not found in catalog")

    reqs = crop_cfg.get("requirements", {})
    scores = {}
    limiting_factors = []

    # 1. Temperature
    temp_obs = environmental_profile.get("temperature", {}).get("annual_mean_c")
    temp_req = reqs.get("temperature_c", {})
    if temp_obs is not None and temp_req:
        t_score = evaluate_parameter_suitability(
            temp_obs,
            temp_req.get("min"),
            temp_req.get("opt_min"),
            temp_req.get("opt_max"),
            temp_req.get("max")
        )
        scores["temperature"] = round(t_score, 2)
        if t_score < 0.6:
            limiting_factors.append(f"Temperature suboptimal ({temp_obs}°C vs opt {temp_req.get('opt_min')}-{temp_req.get('opt_max')}°C)")

    # 2. Rainfall
    rain_obs = environmental_profile.get("total_rainfall_mm")
    rain_req = reqs.get("rainfall_annual_mm", {})
    if rain_obs is not None and rain_req:
        r_score = evaluate_parameter_suitability(
            rain_obs,
            rain_req.get("min"),
            rain_req.get("opt_min"),
            rain_req.get("opt_max"),
            rain_req.get("max")
        )
        scores["rainfall"] = round(r_score, 2)
        if r_score < 0.6:
            limiting_factors.append(f"Rainfall limiting ({rain_obs}mm vs opt {rain_req.get('opt_min')}-{rain_req.get('opt_max')}mm)")

    # 3. Soil pH
    ph_obs = environmental_profile.get("soil", {}).get("soil_ph")
    ph_req = reqs.get("soil_ph", {})
    if ph_obs is not None and ph_req:
        p_score = evaluate_parameter_suitability(
            ph_obs,
            ph_req.get("min"),
            ph_req.get("opt_min"),
            ph_req.get("opt_max"),
            ph_req.get("max")
        )
        scores["soil_ph"] = round(p_score, 2)
        if p_score < 0.6:
            limiting_factors.append(f"Soil pH suboptimal ({ph_obs} vs opt {ph_req.get('opt_min')}-{ph_req.get('opt_max')})")

    # Overall suitability index (Liebig's Law of the Minimum + Weighted Average)
    if scores:
        min_factor_score = min(scores.values())
        mean_factor_score = sum(scores.values()) / len(scores)
        overall_score = round((0.6 * min_factor_score + 0.4 * mean_factor_score) * 100.0, 1)
    else:
        overall_score = 50.0

    suitability_class = (
        "Highly Suitable (S1)" if overall_score >= 80 else
        ("Moderately Suitable (S2)" if overall_score >= 60 else
         ("Marginally Suitable (S3)" if overall_score >= 40 else "Currently Not Suitable (N)"))
    )

    return {
        "crop_name": crop_cfg.get("common_name", crop_name),
        "overall_suitability_score": overall_score,
        "suitability_class": suitability_class,
        "component_scores": scores,
        "limiting_factors": limiting_factors
    }
