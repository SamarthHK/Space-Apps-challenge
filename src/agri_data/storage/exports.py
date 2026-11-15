"""
Export utilities for saving analytical datasets as Parquet, GeoPackage, GeoJSON, and JSON profiles.
"""

from pathlib import Path
from typing import Dict, Any, Union, Optional
import json
import pandas as pd
import geopandas as gpd
from agri_data.config import settings


def export_fields_spatial(
    gdf: gpd.GeoDataFrame,
    output_dir: Union[str, Path] = None
) -> Dict[str, Path]:
    """
    Exports field GeoDataFrame to GeoJSON, GeoPackage, and Parquet.
    """
    out_dir = Path(output_dir or settings.processed_dir / "fields")
    out_dir.mkdir(parents=True, exist_ok=True)

    geojson_path = out_dir / "fields.geojson"
    gpkg_path = out_dir / "fields.gpkg"
    parquet_path = out_dir / "field_metadata.parquet"

    # Save GeoJSON
    gdf.to_file(geojson_path, driver="GeoJSON")

    # Save GeoPackage
    gdf.to_file(gpkg_path, driver="GPKG")

    # Save Parquet (strip geometry or save WKT for standard tabular parquet readers)
    df_no_geom = gdf.drop(columns=["geometry"]).copy()
    df_no_geom["geometry_wkt"] = gdf.geometry.to_wkt()
    df_no_geom.to_parquet(parquet_path, index=False)

    return {
        "geojson": geojson_path,
        "gpkg": gpkg_path,
        "parquet": parquet_path
    }


def export_observations_parquet(
    df: pd.DataFrame,
    domain: str,
    field_id: str,
    year: Optional[int] = None
) -> Path:
    """
    Saves processed tabular observations as partitioned or field-specific Parquet files.
    Example: data/processed/climate/field_id=FIELD_0001/daily_weather.parquet
    """
    target_dir = settings.processed_dir / domain / f"field_id={field_id}"
    if year:
        target_dir = target_dir / f"year={year}"
    target_dir.mkdir(parents=True, exist_ok=True)

    out_file = target_dir / "observations.parquet"
    df.to_parquet(out_file, index=False)
    return out_file


def export_agricultural_profile(
    field_id: str,
    profile_data: Dict[str, Any],
    output_dir: Union[str, Path] = None
) -> Path:
    """
    Exports a comprehensive JSON agricultural profile for a single plot.
    """
    out_dir = Path(output_dir or settings.exports_dir / field_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_file = out_dir / "agricultural_profile.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(profile_data, f, indent=2, default=str)
    return out_file
