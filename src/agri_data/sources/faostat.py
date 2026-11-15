"""
FAOSTAT and State Agriculture Department Performance Adapter.
Provides regional historical crop yields, cultivated area, and yield stability statistics.
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from shapely.geometry.base import BaseGeometry
from agri_data.config import settings
from .base import BaseDataSource


class FAOSTATAdapter(BaseDataSource):
    """Adapter for FAOSTAT and state-level crop productivity benchmarks."""

    def __init__(self):
        super().__init__(source_id="faostat", domain="crop_performance")
        # Karnataka state & Mandya district historical yield benchmarks (kg/ha)
        self.benchmarks = {
            "sugarcane": {"district_avg_kg_ha": 98500.0, "state_avg_kg_ha": 86000.0, "cv_yield_pct": 12.5},
            "ragi": {"district_avg_kg_ha": 2350.0, "state_avg_kg_ha": 1950.0, "cv_yield_pct": 18.2},
            "pigeonpea": {"district_avg_kg_ha": 1150.0, "state_avg_kg_ha": 920.0, "cv_yield_pct": 24.0},
            "groundnut": {"district_avg_kg_ha": 1680.0, "state_avg_kg_ha": 1420.0, "cv_yield_pct": 21.5},
            "maize": {"district_avg_kg_ha": 4450.0, "state_avg_kg_ha": 3800.0, "cv_yield_pct": 15.0}
        }

    def retrieve(
        self,
        geometry: Optional[BaseGeometry] = None,
        variables: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        field_id: Optional[str] = None,
        crop_name: str = "ragi"
    ) -> Dict[str, Any]:
        data = self.benchmarks.get(crop_name.lower(), {
            "district_avg_kg_ha": 2000.0, "state_avg_kg_ha": 1800.0, "cv_yield_pct": 20.0
        })
        return {
            "crop": crop_name,
            "region": "Karnataka - Mandya District",
            "benchmark_data": data
        }

    def process(self, raw_data: Dict[str, Any], geometry: Optional[BaseGeometry] = None) -> Dict[str, Any]:
        b = raw_data.get("benchmark_data", {})
        return {
            "source_id": "faostat",
            "crop": raw_data.get("crop"),
            "region": raw_data.get("region"),
            "district_yield_kg_ha": b.get("district_avg_kg_ha"),
            "state_yield_kg_ha": b.get("state_avg_kg_ha"),
            "yield_variability_cv": b.get("cv_yield_pct")
        }

    def validate(self, processed_data: Dict[str, Any]) -> bool:
        return "district_yield_kg_ha" in processed_data
