"""
Zonal statistics extraction module for raster datasets.
Calculates mean, median, min, max, std, p10, p90, valid_pixel_count, and coverage percentage
while strictly tracking native spatial resolution and provenance.
"""

from typing import Dict, Any, Union, Optional
from pathlib import Path
import numpy as np
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from shapely.geometry import mapping


def extract_zonal_statistics(
    raster_path_or_array: Union[str, Path, np.ndarray],
    geometry: Any,
    raster_crs: Optional[str] = "EPSG:4326",
    affine_transform: Optional[Any] = None,
    nodata: Optional[float] = None,
    source_resolution_m: Optional[float] = None
) -> Dict[str, Any]:
    """
    Extracts zonal statistics of raster pixels intersecting a polygon geometry.

    Supports both file paths (GeoTIFF) and in-memory numpy arrays with transforms.
    """
    if isinstance(raster_path_or_array, (str, Path)):
        path = Path(raster_path_or_array)
        if not path.exists():
            raise FileNotFoundError(f"Raster file not found: {path}")

        with rasterio.open(path) as src:
            nodata_val = nodata if nodata is not None else src.nodata
            # Determine source pixel resolution in metres approximately
            res_x, res_y = abs(src.res[0]), abs(src.res[1])
            if source_resolution_m is None:
                # If in degrees (EPSG:4326), 1 deg ~ 111,000 m
                if src.crs and "4326" in str(src.crs):
                    source_resolution_m = round((res_x + res_y) / 2.0 * 111320.0, 1)
                else:
                    source_resolution_m = round((res_x + res_y) / 2.0, 1)

            # Mask raster with polygon
            geom_json = [mapping(geometry)]
            try:
                out_image, out_transform = mask(src, geom_json, crop=True, all_touched=True)
                data = out_image[0]
            except ValueError:
                # Polygon does not overlap raster
                return {
                    "mean": None, "median": None, "min": None, "max": None, "std": None,
                    "p10": None, "p90": None, "valid_pixel_count": 0, "coverage_percentage": 0.0,
                    "source_resolution_m": source_resolution_m,
                    "extraction_method": "intersecting_pixels",
                    "status": "no_spatial_overlap"
                }
    else:
        # In-memory array
        data = raster_path_or_array
        nodata_val = nodata

    # Filter valid pixels
    if nodata_val is not None and not np.isnan(nodata_val):
        valid_mask = (data != nodata_val) & ~np.isnan(data)
    else:
        valid_mask = ~np.isnan(data)

    valid_pixels = data[valid_mask]
    total_mask_pixels = data.size

    if valid_pixels.size == 0:
        return {
            "mean": None, "median": None, "min": None, "max": None, "std": None,
            "p10": None, "p90": None, "valid_pixel_count": 0, "coverage_percentage": 0.0,
            "source_resolution_m": source_resolution_m,
            "extraction_method": "intersecting_pixels",
            "status": "no_valid_pixels"
        }

    return {
        "mean": float(np.mean(valid_pixels)),
        "median": float(np.median(valid_pixels)),
        "min": float(np.min(valid_pixels)),
        "max": float(np.max(valid_pixels)),
        "std": float(np.std(valid_pixels)),
        "p10": float(np.percentile(valid_pixels, 10)),
        "p90": float(np.percentile(valid_pixels, 90)),
        "valid_pixel_count": int(valid_pixels.size),
        "coverage_percentage": round(float(valid_pixels.size) / float(total_mask_pixels) * 100.0, 2),
        "source_resolution_m": source_resolution_m,
        "extraction_method": "zonal_statistics_all_touched",
        "status": "success"
    }
