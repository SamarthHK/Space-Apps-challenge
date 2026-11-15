"""
Weather station and monitoring well matching utilities.
Calculates geodesic distance, nearest stations, elevation differential, and representativeness score.
"""

from typing import List, Dict, Any, Optional
import math
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


def haversine_distance_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Calculates great-circle distance between two coordinates in kilometres."""
    r = 6371.0  # Earth's radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def find_nearest_stations(
    field_lon: float,
    field_lat: float,
    stations_df: pd.DataFrame,
    field_elevation_m: Optional[float] = None,
    max_radius_km: float = 50.0,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Finds the nearest stations (e.g. KSNDMC, IMD rain gauges, CGWB monitoring wells)
    to a field centroid, computing distance, elevation diff, and representativeness.

    Expects stations_df to have columns:
    ['station_id', 'station_name', 'longitude', 'latitude', (optional) 'elevation_m', (optional) 'station_type']
    """
    matches = []
    for _, st in stations_df.iterrows():
        dist_km = haversine_distance_km(field_lon, field_lat, st["longitude"], st["latitude"])
        if dist_km <= max_radius_km:
            st_elev = st.get("elevation_m")
            elev_diff = None
            if field_elevation_m is not None and st_elev is not None and not pd.isna(st_elev):
                elev_diff = abs(field_elevation_m - float(st_elev))

            # Representativeness score: based on distance and elevation difference
            # 1.0 is perfect, decays with distance and elevation discrepancy
            score = 1.0 / (1.0 + (dist_km / 10.0))
            if elev_diff is not None:
                score *= 1.0 / (1.0 + (elev_diff / 100.0))

            matches.append({
                "station_id": str(st["station_id"]),
                "station_name": str(st.get("station_name", "Unknown Station")),
                "station_type": str(st.get("station_type", "weather")),
                "distance_km": round(dist_km, 2),
                "distance_m": round(dist_km * 1000.0, 1),
                "station_lon": float(st["longitude"]),
                "station_lat": float(st["latitude"]),
                "station_elevation_m": float(st_elev) if st_elev is not None and not pd.isna(st_elev) else None,
                "elevation_diff_m": round(elev_diff, 1) if elev_diff is not None else None,
                "representativeness_score": round(score, 3)
            })

    matches.sort(key=lambda x: x["distance_km"])
    return matches[:top_k]
