"""
Geospatial processing modules: KML parsing, geometry validation, area calculation,
spatial buffering, station matching, and zonal statistics.
"""

from .kml import load_kml, parse_kml_or_kmz
from .geometry import validate_and_repair_geometry, calculate_centroids
from .area import calculate_area_and_perimeter, get_utm_crs_for_lon_lat
from .buffers import generate_field_buffers
from .stations import find_nearest_stations
from .zonal_statistics import extract_zonal_statistics

__all__ = [
    "load_kml",
    "parse_kml_or_kmz",
    "validate_and_repair_geometry",
    "calculate_centroids",
    "calculate_area_and_perimeter",
    "get_utm_crs_for_lon_lat",
    "generate_field_buffers",
    "find_nearest_stations",
    "extract_zonal_statistics",
]
