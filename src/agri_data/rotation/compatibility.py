"""Crop-pair compatibility and rotation constraints."""

from typing import Any, Dict, Iterable, List
from agri_data.config import settings


def get_rotation_compatibility(previous_crop: str, next_crop: str) -> Dict[str, Any]:
    previous, following = previous_crop.lower(), next_crop.lower()
    pairs = settings.crop_catalog_cfg.get("rotation_compatibility", {}).get("pairs", [])
    for pair in pairs:
        if pair.get("previous") == previous and pair.get("next") == following:
            return {"previous_crop": previous, "next_crop": following, **pair, "status": "catalogued"}
    return {"previous_crop": previous, "next_crop": following, "compatibility_score": 5.0,
            "expected_yield_delta_pct": 0.0, "status": "unscored", "notes": "No catalog pair"}


def rank_next_crops(previous_crop: str, candidates: Iterable[str]) -> List[Dict[str, Any]]:
    results = [get_rotation_compatibility(previous_crop, candidate) for candidate in candidates]
    return sorted(results, key=lambda item: item.get("compatibility_score", 0), reverse=True)
