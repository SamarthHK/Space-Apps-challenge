"""
Processing package: soil hydraulics, climate aggregation, drought indices,
terrain analysis, vegetation metrics, quality control, and unit conversions.
"""

from .soil import classify_usda_texture, estimate_hydraulic_properties, process_soil_profile
from .climate import aggregate_climate_metrics
from .drought import (
    calculate_dry_spells, calculate_growing_degree_days,
    calculate_vapour_pressure_deficit, calculate_hargreaves_et0,
    calculate_comprehensive_drought_indicators
)
from .terrain import calculate_terrain_derivatives_from_elevation
from .vegetation import compute_spectral_indices, extract_phenology_metrics
from .quality_control import validate_variable_range, validate_soil_particle_sum, classify_missing_reason
from .unit_conversion import (
    convert_organic_carbon_to_organic_matter,
    convert_precipitation_mm_to_m3_per_ha,
    convert_yield_kg_ha_to_quintals_acre
)

__all__ = [
    "classify_usda_texture",
    "estimate_hydraulic_properties",
    "process_soil_profile",
    "aggregate_climate_metrics",
    "calculate_dry_spells",
    "calculate_growing_degree_days",
    "calculate_vapour_pressure_deficit",
    "calculate_hargreaves_et0",
    "calculate_comprehensive_drought_indicators",
    "calculate_terrain_derivatives_from_elevation",
    "compute_spectral_indices",
    "extract_phenology_metrics",
    "validate_variable_range",
    "validate_soil_particle_sum",
    "classify_missing_reason",
    "convert_organic_carbon_to_organic_matter",
    "convert_precipitation_mm_to_m3_per_ha",
    "convert_yield_kg_ha_to_quintals_acre",
]
