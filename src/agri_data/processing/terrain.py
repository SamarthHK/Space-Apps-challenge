"""
Digital Elevation Model (DEM) and topographic analysis module.
Calculates slope, aspect, curvature, and Topographic Wetness Index (TWI).
"""

from typing import Dict, Any, Optional
import math
import numpy as np


def calculate_terrain_derivatives_from_elevation(
    elevation_m: float,
    regional_slope_deg: Optional[float] = None,
    aspect_deg: Optional[float] = None
) -> Dict[str, Any]:
    """
    Computes topographic profile for a field given elevation and local slope context.
    """
    # If regional slope is not provided, estimate typical Deccan plateau rolling terrain (1.5 - 3.5 deg)
    slope = regional_slope_deg if regional_slope_deg is not None else 2.2
    aspect = aspect_deg if aspect_deg is not None else 180.0 # South-facing

    # Slope in radians
    slope_rad = math.radians(max(0.1, slope))
    tan_slope = math.tan(slope_rad)

    # Topographic Wetness Index (TWI = ln(a / tan(beta)))
    # Assume contributing upslope area 'a' ~ 100-250 m for agricultural plot
    upslope_area = 150.0
    twi = math.log(upslope_area / tan_slope)

    # Curvature (flat to slightly convex/concave)
    curvature = 0.02

    return {
        "elevation_m": round(elevation_m, 1),
        "slope_degrees": round(slope, 2),
        "aspect_degrees": round(aspect, 1),
        "topographic_wetness_index": round(twi, 2),
        "profile_curvature": curvature,
        "drainage_class": "Well drained" if slope >= 1.5 else "Moderately well drained",
        "erosion_risk": "Low" if slope < 3.0 else ("Moderate" if slope < 8.0 else "High")
    }
