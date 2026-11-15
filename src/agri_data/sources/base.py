"""
Base abstract class for all agricultural and environmental data source adapters.
Ensures standardized acquisition, caching, validation, and storage interfaces.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from shapely.geometry.base import BaseGeometry
import json
import hashlib
from agri_data.config import settings


class BaseDataSource(ABC):
    """
    Standard interface for all source adapters (REST API, Geospatial, Datasets, Models).
    """

    def __init__(self, source_id: str, domain: str):
        self.source_id = source_id
        self.domain = domain
        self.config = settings.get_source(source_id)

    @abstractmethod
    def retrieve(
        self,
        geometry: BaseGeometry,
        variables: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        field_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetches raw data from external API or local source file."""
        pass

    @abstractmethod
    def process(self, raw_data: Dict[str, Any], geometry: BaseGeometry) -> Dict[str, Any]:
        """Cleans, normalizes, and extracts plot-level observations."""
        pass

    @abstractmethod
    def validate(self, processed_data: Dict[str, Any]) -> bool:
        """Validates ranges, completeness, and physical plausibility."""
        pass

    def get_cache_path(self, key_identifier: str, extension: str = "json") -> Path:
        """Computes deterministic cache path based on query hash."""
        cache_dir = settings.cache_dir / self.domain
        cache_dir.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256(key_identifier.encode("utf-8")).hexdigest()[:16]
        return cache_dir / f"{self.source_id}_{h}.{extension}"
