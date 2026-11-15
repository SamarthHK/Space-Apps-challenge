"""
Area, perimeter, and projected coordinate system utilities.
Ensures calculations are performed using projected CRS (equal-area or UTM), never raw lat/lon.
"""

from typing import Union
import geopandas as gpd
import pyproj


def get_utm_crs_for_lon_lat(lon: float, lat: float) -> str:
    """
    Determines the appropriate UTM EPSG code for a given longitude and latitude.
    For India:
    - Longitudes ~68-74: UTM Zone 42N (EPSG:32642)
    - Longitudes ~74-80: UTM Zone 43N (EPSG:32643)  (e.g., Karnataka)
    - Longitudes ~80-86: UTM Zone 44N (EPSG:32644)
    - Longitudes ~86-92: UTM Zone 45N (EPSG:32645)
    - Longitudes ~92-98: UTM Zone 46N (EPSG:32646)
    """
    zone_number = int((lon + 180) / 6) + 1
    if lat >= 0:
        return f"EPSG:{32600 + zone_number}"
    else:
        return f"EPSG:{32700 + zone_number}"


def calculate_area_and_perimeter(
    gdf: gpd.GeoDataFrame,
    method: str = "equal_area",
    equal_area_epsg: str = "EPSG:6933"
) -> gpd.GeoDataFrame:
    """
    Calculates plot area in square metres, hectares, acres, and perimeter in metres
    using a projected CRS.

    Parameters:
        gdf: Input GeoDataFrame with geometries in EPSG:4326.
        method: "equal_area" (EPSG:6933) or "utm" (auto UTM zone from plot centroid).
        equal_area_epsg: The equal-area CRS to use when method='equal_area'.
    """
    res = gdf.copy()
    if res.crs is None:
        res = res.set_crs("EPSG:4326")
    elif res.crs.to_string() != "EPSG:4326":
        res = res.to_crs("EPSG:4326")

    area_sqm_list = []
    area_ha_list = []
    area_acres_list = []
    perimeter_m_list = []
    utm_crs_list = []

    for idx, row in res.iterrows():
        geom = row.geometry
        rep = geom.representative_point()
        utm_crs = get_utm_crs_for_lon_lat(rep.x, rep.y)
        utm_crs_list.append(utm_crs)

        target_crs = equal_area_epsg if method == "equal_area" else utm_crs

        # Reproject single geometry
        single_gdf = gpd.GeoDataFrame([{"geometry": geom}], crs="EPSG:4326").to_crs(target_crs)
        proj_geom = single_gdf.iloc[0].geometry

        sqm = float(proj_geom.area)
        ha = sqm / 10000.0
        acres = ha * 2.47105
        perim = float(proj_geom.length)

        area_sqm_list.append(round(sqm, 2))
        area_ha_list.append(round(ha, 4))
        area_acres_list.append(round(acres, 4))
        perimeter_m_list.append(round(perim, 2))

    res["area_sqm"] = area_sqm_list
    res["area_ha"] = area_ha_list
    res["area_acres"] = area_acres_list
    res["perimeter_m"] = perimeter_m_list
    res["utm_crs"] = utm_crs_list

    return res
