"""Crop-residue production and decomposition estimates."""

from typing import Any, Dict
from agri_data.config import settings


def estimate_residue_dynamics(crop_name: str, yield_tonnes_ha: float,
                              incorporation: bool = True,
                              days_after_harvest: int = 0) -> Dict[str, Any]:
    """Estimate residue carbon and nitrogen remaining after harvest.

    This is a transparent first-order model.  It is not a substitute for a
    calibrated decomposition model, so the returned values include assumptions.
    """
    crop = settings.get_crop(crop_name.lower())
    if not crop:
        raise ValueError(f"Crop '{crop_name}' not found in catalog")
    residue_kg_ha = float(crop.get("residue_kg_ha", 0.0))
    cn_ratio = float(crop.get("residue_c_n_ratio") or 40.0)
    fraction_remaining = max(0.0, min(1.0, 0.92 ** (max(days_after_harvest, 0) / 30.0)))
    if not incorporation:
        fraction_remaining *= 0.75
    remaining = residue_kg_ha * fraction_remaining
    return {
        "crop": crop.get("common_name", crop_name),
        "yield_tonnes_ha": float(yield_tonnes_ha),
        "residue_input_kg_ha": round(residue_kg_ha, 1),
        "residue_remaining_kg_ha": round(remaining, 1),
        "residue_nitrogen_kg_ha": round(remaining / cn_ratio, 1),
        "carbon_to_nitrogen_ratio": cn_ratio,
        "incorporated": incorporation,
        "days_after_harvest": int(days_after_harvest),
        "assumptions": {"monthly_remaining_fraction": 0.92, "model": "first_order_decay"},
    }
