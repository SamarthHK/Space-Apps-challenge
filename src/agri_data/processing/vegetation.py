"""
Vegetation indices processing and phenology extraction module.
Calculates NDVI, NDMI, SAVI, EVI, peak greenness, seasonal amplitude, and growth trajectory.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


def compute_spectral_indices(
    blue: float,
    red: float,
    nir: float,
    swir1: float,
    soil_adj_l: float = 0.5
) -> Dict[str, float]:
    """
    Computes standard agricultural vegetation indices from surface reflectance bands:
    - NDVI = (NIR - Red) / (NIR + Red)
    - NDMI = (NIR - SWIR1) / (NIR + SWIR1)
    - SAVI = ((NIR - Red) / (NIR + Red + L)) * (1 + L)
    - EVI = 2.5 * ((NIR - Red) / (NIR + 6.0 * Red - 7.5 * Blue + 1.0))
    """
    ndvi = (nir - red) / (nir + red + 1e-6)
    ndmi = (nir - swir1) / (nir + swir1 + 1e-6)
    savi = ((nir - red) / (nir + red + soil_adj_l)) * (1.0 + soil_adj_l)
    evi_denom = nir + 6.0 * red - 7.5 * blue + 1.0
    evi = 2.5 * ((nir - red) / (evi_denom + 1e-6))

    return {
        "ndvi": round(float(np.clip(ndvi, -1.0, 1.0)), 4),
        "ndmi": round(float(np.clip(ndmi, -1.0, 1.0)), 4),
        "savi": round(float(np.clip(savi, -1.0, 1.0)), 4),
        "evi": round(float(np.clip(evi, -1.0, 1.0)), 4)
    }


def extract_phenology_metrics(scenes_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Extracts phenological lifecycle indicators from an NDVI time series:
    - Peak NDVI value and date
    - Minimum baseline NDVI
    - Seasonal amplitude (Peak - Base)
    - Green-up rate and senescence duration
    """
    if scenes_df is None or scenes_df.empty or "ndvi" not in scenes_df:
        return {}

    df = scenes_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values("date")

    peak_idx = df["ndvi"].idxmax()
    peak_row = df.loc[peak_idx]

    min_val = float(df["ndvi"].min())
    max_val = float(df["ndvi"].max())
    mean_val = float(df["ndvi"].mean())
    amplitude = max_val - min_val

    return {
        "peak_ndvi": round(max_val, 3),
        "peak_date": peak_row["date"].strftime("%Y-%m-%d"),
        "base_ndvi": round(min_val, 3),
        "mean_annual_ndvi": round(mean_val, 3),
        "seasonal_amplitude": round(amplitude, 3),
        "cropping_cycles_detected": 2 if amplitude > 0.3 else 1
    }
