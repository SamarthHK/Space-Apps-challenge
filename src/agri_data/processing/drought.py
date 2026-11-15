"""
Drought indices, agroclimatic metrics, and reference evapotranspiration (ET0).
Calculates longest dry spell, SPI, Growing Degree Days (GDD), Vapour Pressure Deficit (VPD),
and FAO-56 Penman-Monteith / Hargreaves-Samani reference crop ET.
"""

from typing import Dict, Any, List
import math
import numpy as np
import pandas as pd


def calculate_dry_spells(daily_rainfall: pd.Series, threshold_mm: float = 2.5) -> Dict[str, Any]:
    """
    Identifies dry spells (consecutive days with daily rainfall < threshold_mm).
    Returns maximum consecutive dry days, total dry spells (>7 days), and dry spell events.
    """
    is_dry = (daily_rainfall.fillna(0.0) < threshold_mm).astype(int)
    max_streak = 0
    current_streak = 0
    spells_gt_7 = 0
    spells_gt_14 = 0

    for val in is_dry:
        if val == 1:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
        else:
            if current_streak >= 7:
                spells_gt_7 += 1
            if current_streak >= 14:
                spells_gt_14 += 1
            current_streak = 0

    if current_streak >= 7:
        spells_gt_7 += 1
    if current_streak >= 14:
        spells_gt_14 += 1

    return {
        "longest_dry_spell_days": max_streak,
        "dry_spells_over_7_days": spells_gt_7,
        "dry_spells_over_14_days": spells_gt_14
    }


def calculate_growing_degree_days(
    t_max: pd.Series,
    t_min: pd.Series,
    t_base: float = 10.0,
    t_upper: float = 35.0
) -> Dict[str, Any]:
    """
    Calculates accumulated Growing Degree Days (GDD) using standard agronomic formula:
    GDD = sum(max(0, min(Tmax, Tupper) + max(Tmin, Tbase)) / 2 - Tbase)
    """
    t_max_adj = t_max.clip(lower=t_base, upper=t_upper)
    t_min_adj = t_min.clip(lower=t_base, upper=t_upper)
    daily_gdd = ((t_max_adj + t_min_adj) / 2.0 - t_base).clip(lower=0.0)

    total_accumulated = float(daily_gdd.sum())
    return {
        "base_temp_c": t_base,
        "total_accumulated_gdd": round(total_accumulated, 1),
        "mean_daily_gdd": round(float(daily_gdd.mean()), 1)
    }


def calculate_vapour_pressure_deficit(t_mean_c: float, rh_pct: float) -> float:
    """
    Calculates atmospheric Vapour Pressure Deficit (VPD in kPa).
    Es = 0.6108 * exp((17.27 * T) / (T + 237.3))
    Ea = Es * (RH / 100)
    VPD = Es - Ea
    """
    es = 0.6108 * math.exp((17.27 * t_mean_c) / (t_mean_c + 237.3))
    ea = es * (rh_pct / 100.0)
    vpd = max(0.0, es - ea)
    return round(vpd, 3)


def calculate_hargreaves_et0(
    t_max: float,
    t_min: float,
    t_mean: float,
    lat_deg: float,
    day_of_year: int
) -> float:
    """
    Calculates reference evapotranspiration ET0 (mm/day) using FAO Hargreaves-Samani equation.
    Ra = extraterrestrial radiation estimated from latitude and day of year.
    ET0 = 0.0023 * (Tmean + 17.8) * (Tmax - Tmin)^0.5 * Ra
    """
    # Latitude in radians
    phi = math.radians(lat_deg)
    # Solar declination
    delta = 0.409 * math.sin((2 * math.pi / 365.0) * day_of_year - 1.39)
    # Sunset hour angle
    cos_omega_s = -math.tan(phi) * math.tan(delta)
    cos_omega_s = max(-1.0, min(1.0, cos_omega_s))
    omega_s = math.acos(cos_omega_s)
    # Relative Earth-Sun distance
    dr = 1 + 0.033 * math.cos((2 * math.pi / 365.0) * day_of_year)
    # Solar constant Gsc = 0.0820 MJ/m2/min
    gsc = 0.0820
    # Ra in MJ/m2/day
    ra = (24.0 * 60.0 / math.pi) * gsc * dr * (
        omega_s * math.sin(phi) * math.sin(delta) +
        math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )
    # Convert Ra to equivalent evaporation in mm/day (divide by latent heat ~2.45 MJ/kg)
    ra_mm = max(0.1, ra / 2.45)

    td = max(0.0, t_max - t_min)
    et0 = 0.0023 * (t_mean + 17.8) * math.sqrt(td) * ra_mm
    return round(max(0.1, et0), 2)


def calculate_comprehensive_drought_indicators(
    daily_df: pd.DataFrame,
    latitude_deg: float = 12.52
) -> Dict[str, Any]:
    """
    Aggregates dry spells, GDD, heatwaves, VPD, and annual reference ET0 from daily weather data.
    """
    if daily_df is None or daily_df.empty:
        return {}

    df = daily_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"])

    dry_spell_res = calculate_dry_spells(df["daily_rainfall"])
    gdd_res = calculate_growing_degree_days(df["temperature_max"], df["temperature_min"], t_base=10.0)

    # Heatwave count (Tmax >= 40 C)
    heatwave_days = int((df["temperature_max"] >= 40.0).sum())

    # Daily ET0 sum
    et0_list = []
    vpd_list = []
    for _, row in df.iterrows():
        doy = row["date"].timetuple().tm_yday
        tm = row["temperature_mean"]
        tx = row["temperature_max"]
        tn = row["temperature_min"]
        rh = row.get("relative_humidity", 60.0)

        if pd.notna(tx) and pd.notna(tn) and pd.notna(tm):
            et0_val = calculate_hargreaves_et0(tx, tn, tm, latitude_deg, doy)
            et0_list.append(et0_val)
            vpd_list.append(calculate_vapour_pressure_deficit(tm, rh if pd.notna(rh) else 60.0))

    annual_et0 = round(sum(et0_list), 1) if et0_list else None
    mean_vpd = round(float(np.mean(vpd_list)), 2) if vpd_list else None

    # Aridity index = Total Precipitation / Total Reference ET0
    total_rain = float(df["daily_rainfall"].sum())
    aridity_index = round(total_rain / annual_et0, 2) if annual_et0 and annual_et0 > 0 else None

    return {
        "dry_spells": dry_spell_res,
        "growing_degree_days": gdd_res,
        "heatwave_days_count": heatwave_days,
        "annual_reference_et0_mm": annual_et0,
        "mean_vapour_pressure_deficit_kpa": mean_vpd,
        "aridity_index": aridity_index
    }
