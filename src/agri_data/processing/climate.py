"""
Climate data processing and temporal aggregation module.
Calculates annual and monthly rainfall, rainy day counts, thermal metrics, and seasonal distributions.
"""

from typing import Dict, Any, List
import pandas as pd
import numpy as np


def aggregate_climate_metrics(daily_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes standard agroclimatic indicators from daily meteorological dataframe.
    Expects columns: ['date', 'daily_rainfall', 'temperature_mean', 'temperature_max', 'temperature_min', 'relative_humidity', 'wind_speed', 'solar_radiation']
    """
    if daily_df is None or daily_df.empty:
        return {}

    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    # Rainfall metrics
    rain = df["daily_rainfall"].fillna(0.0)
    annual_rainfall = float(rain.sum())
    rainy_days = int((rain >= 2.5).sum())
    heavy_rain_days = int((rain >= 50.0).sum())

    # Monthly rainfall distribution
    monthly_rain = df.groupby("month")["daily_rainfall"].sum().round(1).to_dict()

    # Temperature metrics
    t_mean = df["temperature_mean"].dropna()
    t_max = df["temperature_max"].dropna()
    t_min = df["temperature_min"].dropna()

    mean_temp = float(t_mean.mean()) if not t_mean.empty else None
    max_temp_recorded = float(t_max.max()) if not t_max.empty else None
    min_temp_recorded = float(t_min.min()) if not t_min.empty else None
    avg_dtr = float((t_max - t_min).mean()) if not t_max.empty and not t_min.empty else None

    # Kharif (June-October) & Rabi (November-February) seasonal rainfall in India
    kharif_rain = float(df[df["month"].isin([6, 7, 8, 9, 10])]["daily_rainfall"].sum())
    rabi_rain = float(df[df["month"].isin([11, 12, 1, 2])]["daily_rainfall"].sum())
    summer_rain = float(df[df["month"].isin([3, 4, 5])]["daily_rainfall"].sum())

    return {
        "total_rainfall_mm": round(annual_rainfall, 1),
        "rainy_days_count": rainy_days,
        "heavy_rain_days_count": heavy_rain_days,
        "monthly_rainfall_mm": monthly_rain,
        "seasonal_rainfall": {
            "kharif_monsoon_mm": round(kharif_rain, 1),
            "rabi_post_monsoon_mm": round(rabi_rain, 1),
            "summer_pre_monsoon_mm": round(summer_rain, 1)
        },
        "temperature": {
            "annual_mean_c": round(mean_temp, 1) if mean_temp else None,
            "absolute_max_c": round(max_temp_recorded, 1) if max_temp_recorded else None,
            "absolute_min_c": round(min_temp_recorded, 1) if min_temp_recorded else None,
            "diurnal_temperature_range_c": round(avg_dtr, 1) if avg_dtr else None
        },
        "mean_relative_humidity_pct": round(float(df["relative_humidity"].mean()), 1) if "relative_humidity" in df and not df["relative_humidity"].dropna().empty else None,
        "mean_solar_radiation_mj_m2_day": round(float(df["solar_radiation"].mean()), 1) if "solar_radiation" in df and not df["solar_radiation"].dropna().empty else None,
        "mean_wind_speed_m_s": round(float(df["wind_speed"].mean()), 1) if "wind_speed" in df and not df["wind_speed"].dropna().empty else None
    }
