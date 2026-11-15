"""Soil-moisture carry-over estimates between crops."""

from typing import Any, Dict


def estimate_moisture_carryover(rainfall_mm: float, et0_mm: float,
                               soil_available_water_mm: float,
                               crop_water_use_mm: float = 0.0,
                               runoff_fraction: float = 0.15) -> Dict[str, Any]:
    """Calculate a bounded end-of-season soil-water balance."""
    if soil_available_water_mm < 0:
        raise ValueError("soil_available_water_mm must be non-negative")
    runoff_fraction = max(0.0, min(1.0, runoff_fraction))
    effective_rain = max(0.0, rainfall_mm) * (1.0 - runoff_fraction)
    water_balance = effective_rain - max(0.0, et0_mm) - max(0.0, crop_water_use_mm)
    carryover = max(0.0, min(float(soil_available_water_mm), water_balance))
    return {
        "effective_rainfall_mm": round(effective_rain, 2),
        "water_balance_mm": round(water_balance, 2),
        "soil_moisture_carryover_mm": round(carryover, 2),
        "soil_available_water_capacity_mm": float(soil_available_water_mm),
        "runoff_fraction": runoff_fraction,
    }
