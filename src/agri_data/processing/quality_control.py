"""
Quality control, range validation, and missing value classification module.
Ensures data consistency and flags implausible or out-of-bounds measurements.
"""

from typing import Dict, Any, List, Tuple
from agri_data.config import settings


def validate_variable_range(var_code: str, value: float) -> Tuple[bool, str]:
    """Checks if a numerical value is within physically valid limits."""
    v_cfg = settings.get_variable(var_code)
    if not v_cfg:
        return True, "UNKNOWN_VARIABLE"

    v_range = v_cfg.get("valid_range")
    if not v_range or len(v_range) < 2:
        return True, "NO_BOUNDS_DEFINED"

    min_val, max_val = v_range[0], v_range[1]
    if min_val is not None and value < min_val:
        return False, f"BELOW_PHYSICAL_MIN ({value} < {min_val})"
    if max_val is not None and value > max_val:
        return False, f"ABOVE_PHYSICAL_MAX ({value} > {max_val})"

    return True, "VALID"


def validate_soil_particle_sum(sand_pct: float, silt_pct: float, clay_pct: float, tolerance: float = 2.0) -> bool:
    """Verifies that sand, silt, and clay sum to approximately 100%."""
    total = sand_pct + silt_pct + clay_pct
    return abs(total - 100.0) <= tolerance


def classify_missing_reason(code: str) -> str:
    """
    Standardizes missing value reasons instead of storing zero:
    - NOT_COLLECTED
    - NOT_AVAILABLE_FROM_SOURCE
    - OUTSIDE_SOURCE_COVERAGE
    - ACCESS_RESTRICTED
    - SENSOR_FAILED
    - NOT_APPLICABLE
    """
    valid_reasons = {
        "NOT_COLLECTED", "NOT_AVAILABLE_FROM_SOURCE", "OUTSIDE_SOURCE_COVERAGE",
        "ACCESS_RESTRICTED", "COLLECTION_FAILED", "NOT_APPLICABLE", "BELOW_DETECTION_LIMIT"
    }
    return code if code in valid_reasons else "NOT_AVAILABLE_FROM_SOURCE"
