import pandas as pd
from shapely.geometry import Polygon

from agri_data.geo.area import calculate_area_and_perimeter
from agri_data.geo.geometry import validate_and_repair_geometry
from agri_data.processing.climate import aggregate_climate_metrics
from agri_data.processing.unit_conversion import convert_precipitation_mm_to_m3_per_ha


def test_area_is_calculated_in_metric_units():
    polygon = Polygon([(76.8, 12.5), (76.801, 12.5), (76.801, 12.501), (76.8, 12.501)])
    result = calculate_area_and_perimeter(__import__("geopandas").GeoDataFrame({"geometry": [polygon]}, crs="EPSG:4326"))
    assert result.loc[0, "area_ha"] > 0
    assert result.loc[0, "perimeter_m"] > 0


def test_invalid_polygon_is_repaired_or_rejected_cleanly():
    repaired, was_repaired, reason = validate_and_repair_geometry(
        Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    )
    assert repaired is not None and repaired.is_valid
    assert was_repaired
    assert reason.startswith("Repaired")


def test_climate_aggregation_and_units():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=3),
        "daily_rainfall": [0, 3, 55], "temperature_mean": [20, 21, 22],
        "temperature_max": [25, 26, 27], "temperature_min": [15, 16, 17],
        "relative_humidity": [50, 60, 70], "wind_speed": [2, 2, 2],
        "solar_radiation": [15, 15, 15],
    })
    metrics = aggregate_climate_metrics(df)
    assert metrics["total_rainfall_mm"] == 58.0
    assert metrics["heavy_rain_days_count"] == 1
    assert convert_precipitation_mm_to_m3_per_ha(1) == 10.0
