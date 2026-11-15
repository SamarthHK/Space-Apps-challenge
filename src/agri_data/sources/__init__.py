"""
Data sources package: ISRIC SoilGrids, NASA POWER, Soil Health Card, CGWB, Sentinel-2, EcoCrop, FAOSTAT.
"""

from .base import BaseDataSource
from .soilgrids import SoilGridsClient
from .nasa_power import NasaPowerClient
from .soil_health_card import SoilHealthCardImporter
from .cgwb import CGWBGroundwaterAdapter
from .gee import SatelliteImageryAdapter
from .ecocrop import EcoCropAdapter
from .faostat import FAOSTATAdapter

__all__ = [
    "BaseDataSource",
    "SoilGridsClient",
    "NasaPowerClient",
    "SoilHealthCardImporter",
    "CGWBGroundwaterAdapter",
    "SatelliteImageryAdapter",
    "EcoCropAdapter",
    "FAOSTATAdapter",
]
