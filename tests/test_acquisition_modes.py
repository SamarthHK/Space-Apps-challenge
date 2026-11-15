from agri_data.geo.kml import load_kml
from agri_data.pipeline.acquisition import acquire_field_data


def test_live_never_returns_reference_satellite_or_well_values():
    field = load_kml("data/input/farm_area.kml").iloc[0]
    results = acquire_field_data(field, domains=["water", "historical_land"])
    assert all(result["status"] == "unavailable" for result in results.values())
    assert all(result["observations"] == [] for result in results.values())


def test_demo_labels_every_observation(monkeypatch, tmp_path):
    from agri_data.config import settings
    monkeypatch.setattr(settings, "raw_dir", tmp_path)
    field = load_kml("data/input/farm_area.kml").iloc[0]
    results = acquire_field_data(field, mode="demo", start_date="2025-01-01", end_date="2025-01-15")
    for result in results.values():
        assert result["status"] == "synthetic"
        for observation in result["observations"]:
            assert observation["measurement_type"] == "synthetic"
