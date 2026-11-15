"""
Configuration manager for the AgriData platform.
Loads settings from YAML files and environment variables.
"""

from pathlib import Path
import os
import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_yaml(file_path: Path) -> dict:
    """Safely loads a YAML file if it exists, returning empty dict if missing."""
    if not file_path.exists():
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class Settings:
    """Central configuration class."""

    def __init__(self, config_dir: Path = CONFIG_DIR):
        self.config_dir = config_dir
        self.project_cfg = load_yaml(config_dir / "project.yaml")
        self.sources_cfg = load_yaml(config_dir / "sources.yaml")
        self.variables_cfg = load_yaml(config_dir / "variables.yaml")
        self.crop_catalog_cfg = load_yaml(config_dir / "crop_catalog.yaml")
        self.processing_cfg = load_yaml(config_dir / "processing.yaml")

        # Database URL
        self.database_url = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{BASE_DIR / 'data' / 'agri_data.db'}"
        )

        # Paths
        self.data_dir = BASE_DIR / os.getenv("DATA_DIR", "data")
        self.raw_dir = self.data_dir / "raw"
        self.staging_dir = self.data_dir / "staging"
        self.normalized_dir = self.data_dir / "normalized"
        self.processed_dir = self.data_dir / "processed"
        self.derived_dir = self.data_dir / "derived"
        self.exports_dir = self.data_dir / "exports"
        self.cache_dir = self.data_dir / "cache"
        self.logs_dir = BASE_DIR / os.getenv("LOG_DIR", "logs")

        # Ensure essential directories exist
        for d in [
            self.data_dir, self.raw_dir, self.staging_dir,
            self.normalized_dir, self.processed_dir, self.derived_dir,
            self.exports_dir, self.cache_dir, self.logs_dir
        ]:
            d.mkdir(parents=True, exist_ok=True)

        # Coordinate systems
        coord_cfg = self.project_cfg.get("coordinates", {})
        self.default_crs = coord_cfg.get("storage_crs", "EPSG:4326")
        self.equal_area_crs = coord_cfg.get("equal_area_crs", "EPSG:6933")

        # External API Base URLs
        self.soilgrids_base_url = os.getenv(
            "SOILGRIDS_BASE_URL",
            self.sources_cfg.get("sources", {}).get("soilgrids", {}).get("base_url", "https://rest.isric.org/soilgrids/v2.0")
        )
        self.nasa_power_base_url = os.getenv(
            "NASA_POWER_BASE_URL",
            self.sources_cfg.get("sources", {}).get("nasa_power", {}).get("base_url", "https://power.larc.nasa.gov/api/temporal/daily/point")
        )

        # Buffer distances (in metres)
        self.buffers = self.project_cfg.get("buffers_meters", {
            "field_boundary": 0,
            "immediate_surroundings": 100,
            "water_and_drainage": 500,
            "local_environmental": 1000,
            "landscape_hydrological": 5000,
            "regional_stations": 10000
        })

    def get_source(self, source_name: str) -> dict:
        return self.sources_cfg.get("sources", {}).get(source_name, {})

    def get_variable(self, var_name: str) -> dict:
        return self.variables_cfg.get("variables", {}).get(var_name, {})

    def get_crop(self, crop_name: str) -> dict:
        return self.crop_catalog_cfg.get("crops", {}).get(crop_name, {})


settings = Settings()
