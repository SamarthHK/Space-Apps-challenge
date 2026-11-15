"""
Crop rotation nutrient cycling and soil balance module.
Calculates biological nitrogen fixation by legumes, NPK crop uptake, and net soil balance.
"""

from typing import Dict, Any, List
from agri_data.config import settings


def calculate_nutrient_balance(
    crop_name: str,
    achieved_yield_tonnes_ha: float,
    fertilizer_applied_n_p_k_kg_ha: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Computes net soil nutrient balance after harvest:
    Net N = N_fertilizer + N_fixed - N_uptake
    Net P = P_fertilizer - P_uptake
    Net K = K_fertilizer - K_uptake
    """
    crop_cfg = settings.get_crop(crop_name)
    if not crop_cfg:
        return {}

    uptake_rates = crop_cfg.get("nutrient_uptake_kg_per_ton", {"nitrogen": 20.0, "phosphorus": 5.0, "potassium": 25.0})
    n_fixed = crop_cfg.get("nitrogen_fixation_kg_ha", 0.0)

    # Nutrient removal
    n_removal = round(uptake_rates.get("nitrogen", 20.0) * achieved_yield_tonnes_ha, 1)
    p_removal = round(uptake_rates.get("phosphorus", 5.0) * achieved_yield_tonnes_ha, 1)
    k_removal = round(uptake_rates.get("potassium", 25.0) * achieved_yield_tonnes_ha, 1)

    fert = fertilizer_applied_n_p_k_kg_ha or {"nitrogen": 0.0, "phosphorus": 0.0, "potassium": 0.0}
    n_app = fert.get("nitrogen", 0.0)
    p_app = fert.get("phosphorus", 0.0)
    k_app = fert.get("potassium", 0.0)

    net_n = round(n_app + n_fixed - n_removal, 1)
    net_p = round(p_app - p_removal, 1)
    net_k = round(k_app - k_removal, 1)

    return {
        "crop": crop_cfg.get("common_name", crop_name),
        "yield_tonnes_ha": achieved_yield_tonnes_ha,
        "biological_n_fixed_kg_ha": n_fixed,
        "nutrient_uptake_kg_ha": {
            "nitrogen": n_removal,
            "phosphorus": p_removal,
            "potassium": k_removal
        },
        "fertilizer_applied_kg_ha": fert,
        "net_soil_balance_kg_ha": {
            "nitrogen": net_n,
            "phosphorus": net_p,
            "potassium": net_k
        },
        "soil_impact": "Enriching" if net_n > 0 else "Depleting"
    }
