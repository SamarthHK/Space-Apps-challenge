"""
Geometry validation, repair, centroid and bounding box utilities.
"""

from typing import Tuple, Dict, Any
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.validation import make_valid, explain_validity
from .area import get_utm_crs_for_lon_lat


def validate_and_repair_geometry(geom: Any) -> Tuple[Any, bool, str]:
    """
    Validates a shapely geometry.
    If invalid, attempts repair with make_valid.
    Returns: (repaired_geom, was_repaired, validity_reason)
    """
    if geom is None or geom.is_empty:
        return None, False, "Geometry is None or empty"

    if geom.is_valid:
        return geom, False, "Valid"

    reason = explain_validity(geom)
    repaired = make_valid(geom)
    # Check if result contains Polygon or MultiPolygon
    if isinstance(repaired, (Polygon, MultiPolygon)):
        return repaired, True, f"Repaired: {reason}"
    
    # In case make_valid returns GeometryCollection, extract polygons
    polygons = [g for g in getattr(repaired, "geoms", []) if isinstance(g, (Polygon, MultiPolygon))]
    if polygons:
        if len(polygons) == 1:
            return polygons[0], True, f"Extracted polygon from collection: {reason}"
        return MultiPolygon(polygons), True, f"Extracted multi-polygon: {reason}"

    return None, False, f"Unrepairable: {reason}"


def calculate_centroids(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Computes centroid and guaranteed interior representative point
    for each plot in EPSG:4326.
    """
    res = gdf.copy()
    # Centroids are calculated in a local metric CRS, then transformed back;
    # calculating them directly in EPSG:4326 can be materially inaccurate.
    centroid_points = []
    rep_points = []
    for geom in res.geometry:
        rep = geom.representative_point()
        local_crs = get_utm_crs_for_lon_lat(rep.x, rep.y)
        projected = gpd.GeoSeries([geom], crs=res.crs or "EPSG:4326").to_crs(local_crs)
        centroid_points.append(gpd.GeoSeries([projected.iloc[0].centroid], crs=local_crs).to_crs("EPSG:4326").iloc[0])
        rep_points.append(rep)
    centroids = gpd.GeoSeries(centroid_points, index=res.index, crs="EPSG:4326")
    rep_points = gpd.GeoSeries(rep_points, index=res.index, crs="EPSG:4326")

    res["centroid_lon"] = centroids.x
    res["centroid_lat"] = centroids.y
    res["rep_lon"] = rep_points.x
    res["rep_lat"] = rep_points.y

    # Also compute bounding box
    bounds = res.geometry.bounds
    res["bbox_minx"] = bounds["minx"]
    res["bbox_miny"] = bounds["miny"]
    res["bbox_maxx"] = bounds["maxx"]
    res["bbox_maxy"] = bounds["maxy"]

    return res
