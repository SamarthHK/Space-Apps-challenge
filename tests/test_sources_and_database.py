import os
from pathlib import Path

from agri_data.geo.kml import load_kml
from agri_data.sources.soilgrids import SoilGridsClient
from agri_data.sources.nasa_power import NasaPowerClient


def test_sample_kml_has_four_fields():
    fields = load_kml(Path("data/input/farm_area.kml"))
    assert len(fields) == 4
    assert fields["field_id"].tolist() == ["FIELD_0001", "FIELD_0002", "FIELD_0003", "FIELD_0004"]


def test_offline_source_fallbacks_return_normalized_records():
    field = load_kml(Path("data/input/farm_area.kml")).iloc[0]
    soil = SoilGridsClient().process(SoilGridsClient().retrieve(field.geometry, offline_fallback=True), field.geometry)
    climate_client = NasaPowerClient()
    climate = climate_client.process(climate_client.retrieve(field.geometry, start_date="2024-01-01", end_date="2024-01-05", offline_fallback=True), field.geometry)
    assert soil["observations"]
    assert not climate["daily_df"].empty
