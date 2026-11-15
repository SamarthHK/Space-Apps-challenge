"""Executable preparatory storage proof using an authentic archived corpus.

This demonstrates shared persistence, not full DB-01..DB-09 acceptance or S02
completion. Domain schemas and corpus-wide scientific validation are outstanding.
"""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys
import uuid

import geopandas as gpd
import pandas as pd
import psycopg
from psycopg.types.json import Jsonb
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

from .inventory import extract_inventory
from .power import normalize_power, PARAMETERS
from .postgres import PostgresStore
from .identity import stable_field_id
from .corpus import COLLECTION
from .canonical import reconcile_reference


def require(condition, message):
    if not condition:
        raise ValueError(message)


def record_digest(records):
    return sha256(json.dumps(
        sorted(records, key=lambda record: record["observation_id"]),
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()


def run_storage_proof(corpus_path: Path, store: PostgresStore, output: Path, repository: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    try:
        return _run_storage_proof(corpus_path, store, output, repository, started)
    except Exception as error:
        failure = {
            "status": "failed", "full_acceptance": False, "started_at": started,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "error_type": type(error).__name__,
            "corpus_manifest": str(corpus_path.resolve()),
            "reason": "Preparatory proof failed; no acceptance success is certified. Inspect the command error.",
        }
        (output / "failure.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        try:
            corpus = json.loads(corpus_path.read_bytes())
            with store.session() as connection:
                connection.execute(
                    "UPDATE extraction_jobs SET status='failed',completed_at=now() WHERE extraction_job_id=%s",
                    (corpus["weather_asset"]["request_id"],),
                )
        except Exception:
            # The file above remains available even if the database is unreachable.
            pass
        raise


def _run_storage_proof(corpus_path, store, output, repository, started):
    corpus = json.loads(corpus_path.read_bytes())
    for key in ("parcel_asset", "weather_asset"):
        asset = corpus[key]
        if sha256(Path(asset["raw_path"]).read_bytes()).hexdigest() != asset["raw_sha256"]:
            raise ValueError("Authentic corpus checksum changed")
    parcel = json.loads(Path(corpus["parcel_asset"]["raw_path"]).read_bytes())
    geometry = shape(parcel["geometry"])
    store.migrate()
    field_id = stable_field_id("public_reference", COLLECTION, parcel["id"])
    # Replaying an existing receipt retains its historic identifiers; aliases
    # resolve those records to the shared field ID in canonical exports.
    with store.session() as connection:
        existing = connection.execute(
            "SELECT acquired_record->>'field_id' FROM acquisition_observations "
            "WHERE extraction_job_id=%s LIMIT 1", (corpus["weather_asset"]["request_id"],),
        ).fetchone()
        if existing:
            field_id = existing[0]
    observations, missing, metadata = normalize_power(corpus["weather_asset"], field_id)
    if not observations:
        raise ValueError("No actual observations available for the storage proof")
    inventory = extract_inventory(repository / "Plan.md")
    features = {f["id"]: f for f in inventory["features"]}
    dataset_id = metadata["dataset_id"]
    store.migrate()
    with store.session() as connection:
        connection.execute(
            "INSERT INTO projects VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            ("public_reference", "Public infrastructure reference", Jsonb({"scope": corpus["scope"]})),
        )
        for key in ("parcel_asset", "weather_asset"):
            asset = corpus[key]
            connection.execute(
                "INSERT INTO source_assets VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (asset["raw_sha256"], asset["raw_sha256"], asset["raw_path"],
                 asset["response_url"], asset["retrieved_at"], Jsonb(asset)),
            )
        connection.execute(
            "INSERT INTO fields VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (field_id, "public_reference",
             parcel["id"] if field_id.startswith("PDOK_") else json.dumps([COLLECTION, parcel["id"]], separators=(",", ":")),
             Jsonb(parcel["properties"])),
        )
        connection.execute(
            "INSERT INTO field_boundaries VALUES (%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),true,NULL) ON CONFLICT DO NOTHING",
            (field_id + ":original", field_id, corpus["parcel_asset"]["raw_sha256"], json.dumps(parcel["geometry"])),
        )
        connection.execute("INSERT INTO data_sources VALUES (%s,%s) ON CONFLICT DO NOTHING",
                           ("SRC-004", Jsonb({"provider": "NASA POWER"})))
        connection.execute("INSERT INTO datasets VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                           (dataset_id, "SRC-004", metadata["header"]["api"]["version"], Jsonb(metadata)))
        for code, (variable_id, feature_id, unit) in PARAMETERS.items():
            connection.execute("INSERT INTO feature_requirements VALUES (%s,%s) ON CONFLICT DO NOTHING",
                               (feature_id, Jsonb(features[feature_id])))
            definition = {
                "unit": unit, "provider_definition": metadata["parameters"][code],
                "status": "pending_scientific_review", "evidence": corpus["weather_asset"]["raw_sha256"],
            }
            connection.execute("INSERT INTO variables VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                               (variable_id, feature_id, Jsonb(definition)))
            connection.execute("INSERT INTO source_bindings VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                               (f"{dataset_id}:{code}", variable_id, dataset_id,
                                f"/properties/parameter/{code}", Jsonb(definition)))
        asset = corpus["weather_asset"]
        connection.execute("INSERT INTO extraction_jobs VALUES (%s,%s,%s,%s,%s,%s) "
                           "ON CONFLICT (extraction_job_id) DO UPDATE SET status='in_progress',completed_at=NULL",
                           (asset["request_id"], asset["raw_sha256"], asset["started_at"],
                            None, "in_progress", Jsonb(asset)))
        inserted = sum(store.save_observation(connection, observation) for observation in observations)

    readback = store.read_observations(asset["request_id"])
    expected = {o.observation_id: o.model_dump(mode="json") for o in observations}
    require({o.observation_id: o.model_dump(mode="json") for o in readback} == expected,
            "Independent SQL readback differs from normalized records")
    with store.session() as connection:
        repeated = sum(store.save_observation(connection, observation) for observation in observations)
        require(repeated == 0, "Repeat import duplicated observations")
        spatial = connection.execute(
            "SELECT ST_IsValid(geometry), ST_SRID(geometry), ST_AsGeoJSON(geometry,15), "
            "ST_Area(ST_Transform(geometry,32631)), ST_Perimeter(ST_Transform(geometry,32631)) "
            "FROM field_boundaries WHERE boundary_id=%s", (field_id + ":original",)
        ).fetchone()
        require(spatial[0] and spatial[1] == 4326, "Invalid stored geometry or SRID")
        require(shape(json.loads(spatial[2])).equals_exact(geometry, 1e-12), "Stored geometry changed")
        pending_count = connection.execute(
            "SELECT count(*) FROM accepted_observations WHERE extraction_job_id=%s", (asset["request_id"],)
        ).fetchone()[0]
        require(pending_count == 0, "Unvalidated observations entered the accepted view")

    projected = transform(Transformer.from_crs(4326, 32631, always_xy=True).transform, geometry)
    # Projection arithmetic tolerance, declared before the comparison, not an agronomic threshold.
    require(abs(spatial[3] - projected.area) <= 0.01, "Independent area comparison failed")
    require(abs(spatial[4] - projected.length) <= 0.001, "Independent perimeter comparison failed")
    fk_rejected = False
    try:
        with store.session() as connection:
            # Use an authentic observation ID, which is not a registered variable ID.
            connection.execute("UPDATE observations SET variable_id=%s WHERE observation_id=%s",
                               (observations[0].observation_id, observations[0].observation_id))
    except psycopg.errors.ForeignKeyViolation:
        fk_rejected = True
    require(fk_rejected, "Database accepted an orphan reference")
    require({o.observation_id: o.model_dump(mode="json")
             for o in store.read_observations(asset["request_id"])} == expected,
            "Rollback changed persisted records")

    process = subprocess.run(
        [sys.executable, "-m", "agri_data.contracts.storage_proof",
         "--read-job", asset["request_id"], "--database", store.database,
         "--user", store.user, "--schema", store.schema, "--connection-env", store.connection_env],
        capture_output=True, text=True, check=True,
    )
    independent = json.loads(process.stdout)
    require(independent["row_count"] == len(observations), "Process readback row count differs")
    expected_hash = sha256(json.dumps(sorted(expected), separators=(",", ":")).encode()).hexdigest()
    require(independent["observation_id_sha256"] == expected_hash, "Process readback IDs differ")
    require(independent["record_sha256"] == record_digest(list(expected.values())),
            "Process readback values or metadata differ")

    records = [observation.model_dump(mode="json") for observation in readback]
    with (output / "pending_observations.jsonl").open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, allow_nan=False) + "\n")
    exported_json = [json.loads(line) for line in (output / "pending_observations.jsonl").read_text(encoding="utf-8").splitlines()]
    require(exported_json == records, "JSONL roundtrip differs")
    pd.DataFrame(records).to_parquet(output / "pending_observations.parquet", index=False)
    parquet = pd.read_parquet(output / "pending_observations.parquet")
    exported_parquet = json.loads(parquet.to_json(orient="records", date_format="iso", double_precision=15))
    require(exported_parquet == records, "Parquet values or metadata differ")
    fields = gpd.GeoDataFrame([{"field_id": field_id, "geometry": geometry}], crs=4326)
    fields.to_file(output / "fields.geojson", driver="GeoJSON")
    fields.to_file(output / "fields.gpkg", driver="GPKG")
    for filename in ("fields.geojson", "fields.gpkg"):
        exported = gpd.read_file(output / filename)
        require(exported.iloc[0]["field_id"] == field_id, "Exported field identifier differs")
        require(exported.geometry.iloc[0].equals_exact(geometry, 1e-12), "Exported geometry differs")
    report = {
        "status": "preparatory_checks_passed", "full_acceptance": False,
        "started_at": started, "completed_at": datetime.now(timezone.utc).isoformat(),
        "database_identity": store.identity(),
        "inserted": inserted, "persisted": len(readback), "second_import_inserted": repeated,
        "pending_records_in_accepted_view": pending_count,
        "independent_process_readback": independent,
        "foreign_key_rejected": fk_rejected, "rollback_verified": True,
        "area_m2_postgis": spatial[3], "area_m2_pyproj_shapely": projected.area,
        "perimeter_m_postgis": spatial[4], "perimeter_m_pyproj_shapely": projected.length,
        "missing_records": missing,
        "corpus_manifest": str(corpus_path.resolve()),
        "remaining_blockers": [
            "S01 full atomic registry and acceptance corpus not complete",
            "Domain entity migrations and complete shared DB acceptance matrix not implemented",
            "Source product semantics, native resolution and independent scientific references remain pending",
            "Records deliberately excluded from accepted_observations",
        ],
    }
    (output / "storage_proof.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest = {
        "run_id": uuid.uuid4().hex, "bundle_kind": "preparatory_storage_proof",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "corpus_sha256": sha256(corpus_path.read_bytes()).hexdigest(),
        "code": [{"path": str(p.relative_to(repository)), "sha256": sha256(p.read_bytes()).hexdigest()}
                 for p in sorted((repository / "src").rglob("*")) if p.suffix in (".py", ".sql")],
        "lock_sha256": sha256((repository / "uv.lock").read_bytes()).hexdigest(),
        "files": [{"path": p.name, "sha256": sha256(p.read_bytes()).hexdigest()} for p in sorted(output.iterdir())],
    }
    temp = output / "manifest.pending"
    temp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    reconcile_reference(store, corpus_path)
    with store.session() as connection:
        connection.execute(
            "UPDATE extraction_jobs SET status='complete',completed_at=now() WHERE extraction_job_id=%s",
            (asset["request_id"],),
        )
    temp.replace(output / "manifest.json")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--read-job", required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--connection-env", default="DATABASE_URL")
    args = parser.parse_args()
    store = PostgresStore(args.database, args.user, args.schema, args.connection_env)
    rows = store.read_observations(args.read_job)
    print(json.dumps({
        "row_count": len(rows),
        "observation_id_sha256": sha256(json.dumps(sorted(r.observation_id for r in rows), separators=(",", ":")).encode()).hexdigest(),
        "record_sha256": record_digest([r.model_dump(mode="json") for r in rows]),
    }))
