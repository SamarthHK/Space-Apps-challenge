"""
Biological risks and crop protection module.
Structures pest and disease susceptibilities, pathogens, weed competition,
and assesses environmental disease favorability based on weather conditions.
"""

from typing import Dict, Any, List
from agri_data.config import settings


def get_crop_biological_profile(crop_name: str) -> Dict[str, Any]:
    """Retrieves pests, pathogens, and fungal risks for a given crop from catalog."""
    crop_cfg = settings.get_crop(crop_name)
    if not crop_cfg:
        return {}

    return {
        "crop": crop_cfg.get("common_name", crop_name),
        "major_pests": crop_cfg.get("pests", []),
        "major_diseases": crop_cfg.get("diseases", [])
    }


def assess_disease_environmental_favorability(
    crop_name: str,
    temperature_c: float,
    relative_humidity_pct: float
) -> List[Dict[str, Any]]:
    """
    Evaluates whether current microclimatic conditions favor disease outbreaks.
    Example:
    - Blast in Ragi: Temp 22-28C and RH > 85%
    - Red Rot in Sugarcane: High humidity (>80%) and warm temp (28-32C)
    - Pod Borer in Pigeonpea: High activity during warm, dry spells (25-32C, RH < 65%)
    """
    risks = []

    if crop_name.lower() in ["ragi", "finger_millet"]:
        if 20.0 <= temperature_c <= 28.0 and relative_humidity_pct >= 80.0:
            risks.append({
                "disease": "Blast (Magnaporthe grisea)",
                "risk_level": "HIGH",
                "trigger_condition": "Prolonged leaf wetness and moderate temps (20-28°C, RH>80%)",
                "recommended_action": "Preventive spray of Tricyclazole or Pseudomonas fluorescens"
            })

    if crop_name.lower() == "sugarcane":
        if 27.0 <= temperature_c <= 34.0 and relative_humidity_pct >= 80.0:
            risks.append({
                "disease": "Red Rot (Colletotrichum falcatum)",
                "risk_level": "MODERATE",
                "trigger_condition": "High humidity and warm conditions during grand growth",
                "recommended_action": "Maintain field drainage, inspect stalks for discolouration"
            })

    if crop_name.lower() == "pigeonpea":
        if 24.0 <= temperature_c <= 32.0 and relative_humidity_pct <= 65.0:
            risks.append({
                "disease": "Pod Borer (Helicoverpa armigera)",
                "risk_level": "HIGH",
                "trigger_condition": "Warm dry spell coinciding with flowering/pod formation",
                "recommended_action": "Install pheromone traps, spray neem formulations or HaNPV"
            })

    return risks
