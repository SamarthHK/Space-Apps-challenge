"""
Soil data processing, USDA texture triangle classification,
and pedotransfer hydraulic property estimation (Field capacity, Wilting point, AWC).
"""

from typing import Dict, Any, Tuple, Optional


def classify_usda_texture(sand: float, silt: float, clay: float) -> str:
    """
    Classifies soil texture according to the standard USDA Soil Texture Triangle.
    Takes percentages of sand, silt, and clay (summing to ~100%).
    """
    # Normalize if slightly off 100
    total = sand + silt + clay
    if total > 0 and abs(total - 100.0) > 0.5:
        sand = (sand / total) * 100.0
        silt = (silt / total) * 100.0
        clay = (clay / total) * 100.0

    if silt + 1.5 * clay < 15:
        return "Sand"
    elif silt + 1.5 * clay >= 15 and silt + 2.0 * clay < 30:
        return "Loamy Sand"
    elif (clay >= 7 and clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50 and silt + 2 * clay >= 30):
        return "Sandy Loam"
    elif clay >= 7 and clay < 27 and silt >= 28 and silt < 50 and sand <= 52:
        return "Loam"
    elif (silt >= 50 and clay >= 12 and clay < 27) or (silt >= 50 and silt < 80 and clay < 12):
        return "Silt Loam"
    elif silt >= 80 and clay < 12:
        return "Silt"
    elif clay >= 20 and clay < 35 and sand > 45 and silt < 28:
        return "Sandy Clay Loam"
    elif clay >= 27 and clay < 40 and sand > 20 and sand <= 45:
        return "Clay Loam"
    elif clay >= 27 and clay < 40 and sand <= 20:
        return "Silty Clay Loam"
    elif clay >= 35 and sand > 45:
        return "Sandy Clay"
    elif clay >= 40 and silt >= 40:
        return "Silty Clay"
    elif clay >= 40:
        return "Clay"
    else:
        return "Loam"


def estimate_hydraulic_properties(
    sand_pct: float,
    clay_pct: float,
    organic_matter_pct: float = 1.5
) -> Dict[str, float]:
    """
    Estimates soil hydraulic properties using Saxton and Rawls (2006) pedotransfer functions:
    - Field Capacity (theta_fc, m3/m3)
    - Permanent Wilting Point (theta_pwp, m3/m3)
    - Available Water Capacity (awc, mm of water per metre of soil depth)
    """
    s = sand_pct / 100.0
    c = clay_pct / 100.0
    om = organic_matter_pct

    # 1. Wilting point theta_1500 (tension 1500 kPa)
    theta_1500 = (
        -0.024 * s + 0.487 * c + 0.006 * om +
        0.005 * (s * om) - 0.013 * (c * om) +
        0.068 * (s * c) + 0.031
    )
    theta_pwp = theta_1500 + (0.14 * theta_1500 - 0.02)

    # 2. Field capacity theta_33 (tension 33 kPa)
    theta_33 = (
        -0.251 * s + 0.195 * c + 0.011 * om +
        0.006 * (s * om) - 0.027 * (c * om) +
        0.452 * (s * c) + 0.299
    )
    theta_fc = theta_33 + (1.283 * (theta_33 ** 2) - 0.374 * theta_33 - 0.015)

    # Bound within physical reality
    theta_pwp = max(0.02, min(0.45, theta_pwp))
    theta_fc = max(theta_pwp + 0.03, min(0.60, theta_fc))

    # AWC in mm/m = (theta_fc - theta_pwp) * 1000 mm/m
    awc_mm_per_m = (theta_fc - theta_pwp) * 1000.0

    return {
        "field_capacity_vol": round(float(theta_fc), 4),
        "permanent_wilting_point_vol": round(float(theta_pwp), 4),
        "available_water_capacity_mm_m": round(float(awc_mm_per_m), 1)
    }


def process_soil_profile(observations: list) -> Dict[str, Any]:
    """
    Aggregates topsoil (0-30 cm) and subsoil properties for agronomic interpretation.
    """
    props = {}
    for o in observations:
        v_id = o["variable_id"]
        val = o["value_numeric"]
        top = o.get("depth_top_cm", 0.0)
        # Focus on topsoil 0-30cm
        if top <= 15:
            if v_id not in props:
                props[v_id] = val

    sand = props.get("sand_content", 50.0)
    silt = props.get("silt_content", 25.0)
    clay = props.get("clay_content", 25.0)
    soc = props.get("organic_carbon", 10.0) # g/kg
    om_pct = (soc / 10.0) * 1.724 # Van Bemmelen conversion factor

    texture_class = classify_usda_texture(sand, silt, clay)
    hydraulics = estimate_hydraulic_properties(sand, clay, om_pct)

    return {
        "texture_class": texture_class,
        "sand_pct": sand,
        "silt_pct": silt,
        "clay_pct": clay,
        "soil_ph": props.get("soil_ph", 6.5),
        "organic_carbon_g_kg": soc,
        "estimated_om_pct": round(om_pct, 2),
        "bulk_density_g_cm3": props.get("bulk_density", 1.35),
        "cation_exchange_capacity": props.get("cation_exchange_capacity", 18.0),
        "hydraulics": hydraulics
    }
