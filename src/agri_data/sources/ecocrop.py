"""
FAO EcoCrop & ICAR Crop Requirements Database Adapter.
Provides minimum, optimum, and maximum biological thresholds for temperature,
rainfall, soil pH, salinity, soil depth, and altitude.
"""

from typing import Dict, Any, List, Optional
from shapely.geometry.base import BaseGeometry
from agri_data.config import settings
from .base import BaseDataSource


class EcoCropAdapter(BaseDataSource):
    """Adapter for FAO EcoCrop & ICAR crop ecological requirements."""

    def __init__(self):
        super().__init__(source_id="fao_ecocrop", domain="crop_requirements")

    def retrieve(
        self,
        geometry: Optional[BaseGeometry] = None,
        variables: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        field_id: Optional[str] = None,
        crop_id: Optional[str] = "ragi"
    ) -> Dict[str, Any]:
        """Fetches crop requirements profile from catalog."""
        crop_data = settings.get_crop(crop_id or "ragi")
        if not crop_data:
            # Fallback
            crop_data = list(settings.crop_catalog_cfg.get("crops", {}).values())[0]
        return crop_data

    def process(self, raw_data: Dict[str, Any], geometry: Optional[BaseGeometry] = None) -> Dict[str, Any]:
        reqs = raw_data.get("requirements", {})
        return {
            "source_id": "fao_ecocrop",
            "crop_id": raw_data.get("id"),
            "common_name": raw_data.get("common_name"),
            "botanical_name": raw_data.get("botanical_name"),
            "requirements": reqs,
            "nutrient_uptake": raw_data.get("nutrient_uptake_kg_per_ton", {}),
            "stages": raw_data.get("stages", {})
        }

    def validate(self, processed_data: Dict[str, Any]) -> bool:
        return "requirements" in processed_data
