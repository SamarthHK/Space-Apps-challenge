"""Geographic checks using the acquired official parcel, not invented coordinates."""

from hashlib import sha256
from pathlib import Path
import json
import uuid

import geopandas as gpd
import yaml
from shapely.geometry import shape

from agri_data.contracts.boundary_import import ingest_boundaries
from agri_data.contracts.geography import parse_boundaries
from agri_data.contracts.postgres import PostgresStore


ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = "https://api.pdok.nl/rvo/gewaspercelen/ogc/v1/collections/brpgewas"


def corpus():
    config = yaml.safe_load((ROOT / "config" / "acceptance.yaml").read_bytes())
    return json.loads((ROOT / config["reference_corpus_manifest"]).read_bytes()), config


def test_actual_kml_parser_preserves_provider_geometry_and_metadata():
    evidence, _ = corpus()
    path = Path(evidence["kml_path"])
    assert sha256(path.read_bytes()).hexdigest() == evidence["kml_sha256"]
    fields, rejected = parse_boundaries(path, "public_reference", NAMESPACE)
    assert not rejected
    parcel = json.loads(Path(evidence["parcel_asset"]["raw_path"]).read_bytes())
    independent = gpd.read_file(path)
    assert len(fields) == len(independent) == 1
    field = fields[0]
    assert field.source_identifier == parcel["id"]
    assert field.original.equals_exact(shape(parcel["geometry"]), 1e-12)
    assert field.geometry.equals_exact(independent.geometry.iloc[0], 1e-12)
    actual_metadata = {item["name"]: item["value"] for item in field.metadata["extended_data"]}
    assert actual_metadata == {key: str(value) for key, value in parcel["properties"].items()}
    independent_metric = independent.to_crs(independent.estimate_utm_crs())
    assert abs(field.area_m2 - independent_metric.area.iloc[0]) <= 0.01
    assert abs(field.perimeter_m - independent_metric.length.iloc[0]) <= 0.001
    assert field.repair_notes is None


def test_real_boundary_import_is_persistent_and_idempotent():
    evidence, config = corpus()
    database = config["database"]
    store = PostgresStore(database["expected_database"], database["expected_user"], database["acceptance_schema"])
    path = Path(evidence["kml_path"])
    output = ROOT / "data" / "exports" / ("geographic-regression-" + uuid.uuid4().hex)
    report = ingest_boundaries(path, "public_reference", NAMESPACE, evidence["boundary_source"], store,
                               output / "first", ROOT / "data" / "raw" / "boundary-imports")
    repeated = ingest_boundaries(path, "public_reference", NAMESPACE, evidence["boundary_source"], store,
                                 output / "repeat", ROOT / "data" / "raw" / "boundary-imports")
    assert report["status"] == repeated["status"] == "complete"
    assert report["full_acceptance"] is False
    assert report["import_id"] == repeated["import_id"]
    with store.session() as connection:
        count = connection.execute(
            "SELECT count(*) FROM boundary_import_records WHERE import_id=%s", (report["import_id"],)
        ).fetchone()[0]
    assert count == report["field_count"] == 1
    assert json.loads((output / "first" / "field_records.json").read_bytes()) == json.loads(
        (output / "repeat" / "field_records.json").read_bytes()
    )
