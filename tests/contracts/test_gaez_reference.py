"""Native-cell and source-binding checks using acquired, not simulated, reference products."""

from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import rasterio

from agri_data.contracts.gaez import build_gaez, raster_values, reference_cells, validate_gaez_corpus
from agri_data.contracts.india_cli import database_store
from agri_data.contracts.model_records import load_model_records
from agri_data.contracts.outcome_data import checked_bytes, write_json


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def corpus():
    value = os.environ.get("AGRI_GAEZ_CORPUS")
    assert value, "Set AGRI_GAEZ_CORPUS to an acquired GAEZ reference corpus"
    return json.loads(Path(value).read_bytes())


def test_real_native_cells_preserve_provider_values_and_units(corpus):
    _, crops = validate_gaez_corpus(corpus)
    assert len(crops) >= 3
    cells = reference_cells(corpus)
    definition = json.loads(checked_bytes(corpus["definitions"]["RES01-PRC"]))
    assert definition["measureUnit"] == "mm"
    asset = corpus["climate"]["HP0120"]["RES01-PRC"]
    values = raster_values(asset, definition, cells)
    position = next(index for index, (value, coverage) in enumerate(values) if value is not None and coverage == 1)
    cell = cells[position]
    with rasterio.open(asset["raw_path"]) as source:
        expected = next(source.sample([(cell["longitude"], cell["latitude"])]))[0]
    assert values[position][0] == float(expected) * definition["scale"] + definition["offset"]
    assert corpus["specification"]["periods"]["HP0120"] == [2001, 2020]


def test_real_but_misbound_crop_or_time_products_are_rejected(corpus):
    wrong = deepcopy(corpus)
    wrong["climate"]["HP8100"]["RES01-PRC"] = corpus["climate"]["HP0120"]["RES01-PRC"]
    with pytest.raises(ValueError, match="period is bound"):
        validate_gaez_corpus(wrong)
    wrong = deepcopy(corpus)
    first = wrong["targets"][0]
    first["raster"] = next(item["raster"] for item in corpus["targets"]
                           if item["selection"]["CROP"] != first["selection"]["CROP"])
    with pytest.raises(ValueError, match="wrong target"):
        validate_gaez_corpus(wrong)


def test_partial_json_grid_metadata_uses_actual_geotiff_and_source_projection(corpus):
    metadata = json.loads(checked_bytes(corpus["definitions"]["RES01-LT2"]))
    assert metadata["srs"]["epsg"] is None and metadata["width"] is None
    asset = corpus["climate"]["HP0120"]["RES01-LT2"]
    with rasterio.open(asset["raw_path"]) as source:
        assert source.crs.to_epsg() == rasterio.crs.CRS.from_string(metadata["srs"]["proj4"]).to_epsg() == 4326
        assert source.width == 4320 and source.height == 2160
    values = raster_values(asset, metadata, reference_cells(corpus)[:3])
    assert any(value is not None and 0 <= value <= 366 for value, _ in values)


def test_real_reference_subset_database_reload_and_shared_environment(corpus, tmp_path):
    selected = deepcopy(corpus)
    selected["specification"].update(crops=["MZE", "WHE"], grid_stride=24,
                                     climate_variables=["RES01-PRC", "RES01-TMP"], static_variables=["HWSDV201"])
    selected["targets"] = [item for item in selected["targets"] if item["selection"]["CROP"] in ("MZE", "WHE")]
    selected["definitions"] = {key: asset for key, asset in selected["definitions"].items()
                               if key in ("RES05-SXX", "RES01-PRC", "RES01-TMP")}
    selected["climate"] = {period: {key: asset for key, asset in values.items() if key in ("RES01-PRC", "RES01-TMP")}
                           for period, values in selected["climate"].items()}
    selected["static"] = {"HWSDV201": selected["static"]["HWSDV201"]}
    used = [selected["catalogue"], selected["boundary"], selected["boundary_metadata"], *selected["definitions"].values()]
    used += [asset for values in selected["climate"].values() for asset in values.values()]
    used += [asset for item in selected["static"].values() for asset in item.values()]
    used += [item["raster"] for item in selected["targets"]]
    selected["assets"] = list({asset["request_id"]: asset for asset in used}.values())
    path = tmp_path / "subset.json"
    write_json(path, selected)
    first = build_gaez(path, tmp_path / "first", database_store(ROOT / "config" / "acceptance.yaml"))
    process = subprocess.run(
        [sys.executable, "-m", "agri_data", "build-gaez-reference", "--corpus", str(path),
         "--config", str(ROOT / "config" / "acceptance.yaml"), "--output", str(tmp_path / "second")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert process.returncode == 0, process.stdout + process.stderr
    assert json.loads(process.stdout)["dataset_id"] == first["dataset_id"]
    weather = load_model_records(tmp_path / "first", "climate_normal")
    targets = load_model_records(tmp_path / "first", "crop_suitability")
    assert len({(row["site_id"], row["period_id"], row["metric_id"]) for row in weather}) == len(weather)
    assert {row["source_crop_id"] for row in targets} == {"MZE", "WHE"}
    assert all(row["evidence_type"] == "modelled_product" and 0 <= row["value"] <= 10000 for row in targets)
    assert all(row["temporal_support"] == "versioned_static_reference"
               for row in load_model_records(tmp_path / "first", "environment_reference"))
