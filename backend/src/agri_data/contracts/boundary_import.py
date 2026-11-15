"""Import real boundaries; geographic preparation is not scientific acceptance."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json

import geopandas as gpd
from psycopg.types.json import Jsonb
from shapely.geometry import mapping, shape

from .geography import parse_boundaries
from .storage_proof import require


def ingest_boundaries(path, project, namespace, origin, store, output, raw_root, *, allow_repair=False,
                      repair_reference=None, repair_area_tolerance_m2=None, repair_shape_tolerance_m2=None):
    if not origin.strip():
        raise ValueError("Original boundary provenance must be explicitly declared")
    output.mkdir(parents=True, exist_ok=False)
    import_id = None
    try:
        digest = sha256(path.read_bytes()).hexdigest()
        repair_options = {
            "repair_reference": repair_reference, "repair_area_tolerance_m2": repair_area_tolerance_m2,
            "repair_shape_tolerance_m2": repair_shape_tolerance_m2,
        }
        context = json.dumps([project, namespace, digest, "boundary-import-2", allow_repair,
                             sha256(repair_reference.read_bytes()).hexdigest() if repair_reference else None,
                             repair_area_tolerance_m2, repair_shape_tolerance_m2], separators=(",", ":"))
        import_id = sha256(context.encode()).hexdigest()
        return _ingest(path, project, namespace, origin, store, output, raw_root,
                       allow_repair, digest, import_id, repair_options)
    except Exception as error:
        failure = {
            "status": "failed", "full_acceptance": False, "error_type": type(error).__name__,
            "input": str(path.resolve()), "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        if import_id:
            try:
                with store.session() as connection:
                    connection.execute(
                        "UPDATE boundary_imports SET status='failed',completed_at=now() WHERE import_id=%s",
                        (import_id,),
                    )
            except Exception as cleanup_error:
                failure["database_failure_recording_error"] = type(cleanup_error).__name__
        (output / "failure.json").write_text(json.dumps(failure, indent=2), encoding="utf-8")
        (output / "manifest.json").unlink(missing_ok=True)
        raise


def _ingest(path, project, namespace, origin, store, output, raw_root, allow_repair, digest, import_id, repair_options):
    payload = path.read_bytes()
    require(sha256(payload).hexdigest() == digest, "Boundary input changed before archival")
    raw_root.mkdir(parents=True, exist_ok=True)
    archived = raw_root / digest
    try:
        with archived.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        require(sha256(archived.read_bytes()).hexdigest() == digest, "Archived boundary bytes changed")
    fields, rejected = parse_boundaries(path, project, namespace, allow_repair=allow_repair, **repair_options)
    require(sha256(path.read_bytes()).hexdigest() == digest, "Boundary input changed during parsing")
    now = datetime.now(timezone.utc).isoformat()
    status = "partial" if fields and rejected else "complete" if fields else "failed"
    store.migrate()
    with store.session() as connection:
        connection.execute(
            "INSERT INTO projects VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (project, project, Jsonb({"declared_source_namespace": namespace})),
        )
        connection.execute(
            "INSERT INTO source_assets VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (digest, digest, str(archived.resolve()), origin, now,
             Jsonb({"input_path": str(path.resolve()), "origin": origin, "imported_at": now,
                    "provenance_status": "declared; independent review still required"})),
        )
        connection.execute(
            "INSERT INTO boundary_imports VALUES (%s,%s,%s,%s,%s,NULL,'in_progress',%s) "
            "ON CONFLICT (import_id) DO UPDATE SET status='in_progress',completed_at=NULL",
            (import_id, project, digest, namespace, "boundary-import-2", Jsonb(rejected)),
        )
        for field in fields:
            record = field.record()
            identifier = json.dumps([namespace, field.source_identifier], separators=(",", ":"))
            connection.execute(
                "INSERT INTO fields VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (field.field_id, project, identifier, Jsonb(field.metadata)),
            )
            boundary_id = sha256(f"{import_id}|{field.field_id}".encode()).hexdigest()
            connection.execute(
                "INSERT INTO field_boundaries "
                "(boundary_id,field_id,source_asset_id,geometry,original,repair_notes,metric_crs,area_m2,perimeter_m) "
                "VALUES (%s,%s,%s,ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (boundary_id, field.field_id, digest, json.dumps(mapping(field.geometry)),
                 field.repair_notes is None, field.repair_notes, field.metric_crs, field.area_m2, field.perimeter_m),
            )
            connection.execute(
                "INSERT INTO boundary_import_records VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (import_id, field.locator, field.field_id, boundary_id,
                 Jsonb(record["original_geometry"]), Jsonb(record)),
            )
    with store.session() as connection:
        rows = connection.execute(
            "SELECT r.context,ST_AsGeoJSON(b.geometry,15),ST_IsValid(b.geometry),ST_SRID(b.geometry),"
            "ST_Area(ST_Transform(b.geometry,split_part(b.metric_crs,':',2)::integer)),"
            "ST_Perimeter(ST_Transform(b.geometry,split_part(b.metric_crs,':',2)::integer)),"
            "ST_Intersects(b.geometry,ST_PointOnSurface(b.geometry)) "
            "FROM boundary_import_records r JOIN field_boundaries b USING (boundary_id) "
            "WHERE r.import_id=%s ORDER BY r.field_id", (import_id,),
        ).fetchall()
    expected = {field.field_id: field for field in fields}
    require(len(rows) == len(expected), "Boundary readback count differs")
    readback = []
    for record, stored, valid, srid, area, perimeter, intersects in rows:
        field = expected[record["field_id"]]
        require(record == json.loads(json.dumps(field.record())), "Boundary context changed in storage")
        require(valid and srid == 4326 and intersects, "PostGIS geometry validity/CRS/intersection failure")
        require(shape(json.loads(stored)).equals_exact(field.geometry, 1e-12), "PostGIS geometry changed")
        require(abs(area - field.area_m2) <= 0.01, "PostGIS area differs from independent pyproj/Shapely")
        require(abs(perimeter - field.perimeter_m) <= 0.001, "PostGIS perimeter differs from pyproj/Shapely")
        readback.append(record)
    (output / "field_records.json").write_text(json.dumps(readback, indent=2, allow_nan=False), encoding="utf-8")
    if readback:
        frame = gpd.GeoDataFrame([
            {"field_id": row["field_id"], "area_ha": row["area_ha"],
             "perimeter_m": row["perimeter_m"], "geometry": shape(row["geometry"])}
            for row in readback
        ], crs=4326)
        for filename, driver in (("fields.geojson", "GeoJSON"), ("fields.gpkg", "GPKG")):
            frame.to_file(output / filename, driver=driver)
            exported = gpd.read_file(output / filename)
            require(len(exported) == len(expected), "Geographic export count differs")
            for row in exported.itertuples():
                field = expected[row.field_id]
                require(row.geometry.equals_exact(field.geometry, 1e-12), "Geographic export geometry differs")
                require(abs(row.area_ha - field.area_m2 / 10000) <= 1e-6, "Exported area differs")
    report = {
        "status": status, "full_acceptance": False, "import_id": import_id,
        "source_asset_sha256": digest, "origin": origin, "field_count": len(readback),
        "rejected_records": rejected, "database_identity": store.identity(),
        "remaining_cases": "Authentic KMZ/folder/holes/multipart/invalid/spatial-product corpus cases not yet certified",
    }
    (output / "boundary_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    manifest = {
        "kind": "boundary_ingestion_preparation", "status": status, "full_acceptance": False,
        "completed_at": now, "input_sha256": digest,
        "files": [{"path": p.name, "sha256": sha256(p.read_bytes()).hexdigest()} for p in sorted(output.iterdir())],
    }
    pending = output / "manifest.pending"
    pending.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pending.replace(output / "manifest.json")
    with store.session() as connection:
        connection.execute(
            "UPDATE boundary_imports SET status=%s,completed_at=now() WHERE import_id=%s", (status, import_id),
        )
    return report
