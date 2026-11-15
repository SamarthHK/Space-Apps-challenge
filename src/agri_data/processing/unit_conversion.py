"""
Unit conversion utilities for standardizing measurements to canonical project units.
"""

from typing import Union


def convert_organic_carbon_to_organic_matter(soc_g_kg: float) -> float:
    """Converts Soil Organic Carbon (g/kg) to Organic Matter percentage using Van Bemmelen factor (1.724)."""
    soc_pct = soc_g_kg / 10.0
    return round(soc_pct * 1.724, 2)


def convert_celsius_to_kelvin(temp_c: float) -> float:
    return temp_c + 273.15


def convert_precipitation_mm_to_m3_per_ha(precip_mm: float) -> float:
    """1 mm of rainfall = 10 m3 of water per hectare."""
    return precip_mm * 10.0


def convert_yield_kg_ha_to_quintals_acre(yield_kg_ha: float) -> float:
    """Standard Indian agricultural market unit conversion (1 quintal = 100 kg, 1 ha = 2.47105 acres)."""
    quintals_ha = yield_kg_ha / 100.0
    return round(quintals_ha / 2.47105, 2)
