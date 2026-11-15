"""
Spatial buffering utilities for surrounding environmental context.
Builds concentric buffer polygons in metric projected coordinates and returns them in EPSG:4326.
"""

from typing import Dict, List, Optional
import geopandas as gpd
from .area import get_utm_crs_for_lon_lat


def generate_field_buffers(
    gdf: gpd.GeoDataFrame,
    buffer_distances_m: Optional[Dict[str, float]] = None
) -> Dict[str, gpd.GeoDataFrame]:
    """
    Generates buffer polygons for each field around the plot boundaries.

    Parameters:
        gdf: GeoDataFrame containing fields in EPSG:4326 with field_id.
        buffer_distances_m: Dictionary mapping buffer labels to distance in metres, e.g.:
            {
                "surroundings_100m": 100.0,
                "water_500m": 500.0,
                "local_1km": 1000.0,
                "landscape_5km": 5000.0,
                "regional_10km": 10000.0
            }

    Returns:
        Dict[str, gpd.GeoDataFrame] mapping buffer label to buffered GeoDataFrame in EPSG:4326.
    """
    if buffer_distances_m is None:
        buffer_distances_m = {
            "surroundings_100m": 100.0,
            "water_500m": 500.0,
            "local_1km": 1000.0,
            "landscape_5km": 5000.0,
            "regional_10km": 10000.0
        }

    buffer_results = {}

    for label, dist_m in buffer_distances_m.items():
        buffered_rows = []
        for idx, row in gdf.iterrows():
            geom = row.geometry
            rep = geom.representative_point()
            utm_crs = get_utm_crs_for_lon_lat(rep.x, rep.y)

            # Reproject to UTM, buffer, then reproject back to 4326
            geom_utm = gpd.GeoSeries([geom], crs="EPSG:4326").to_crs(utm_crs).iloc[0]
            buffered_utm = geom_utm.buffer(dist_m)
            buffered_4326 = gpd.GeoSeries([buffered_utm], crs=utm_crs).to_crs("EPSG:4326").iloc[0]

            new_row = row.copy()
            new_row.geometry = buffered_4326
            new_row["buffer_label"] = label
            new_row["buffer_distance_m"] = dist_m
            buffered_rows.append(new_row)

        buffer_gdf = gpd.GeoDataFrame(buffered_rows, crs="EPSG:4326")
        buffer_results[label] = buffer_gdf

    return buffer_results
