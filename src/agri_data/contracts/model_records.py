"""Canonical model/reference records with dataset-scoped immutable source evidence."""

from hashlib import sha256
import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from psycopg.types.json import Jsonb

from .identity import fingerprint
from .outcome_data import checked_bytes, write_json
from .storage_proof import require


def model_record(kind, context, values, site_id=None):
    reserved = {"record_id", "context_id", "record_kind", "site_id"}
    require(not reserved & values.keys(), "Model payload uses reserved identity fields")
    body = {"record_kind": kind, "context_id": fingerprint(context), "site_id": site_id, **values}
    return {"record_id": fingerprint(body), **body}


def source_evidence(record, asset, locator, role="value"):
    return {"record_id": record["record_id"], "source_asset_id": asset["raw_sha256"],
            "source_locator": locator, "evidence_role": role}


def verify_model_bundle(path, expected_kind=None):
    path = Path(path).resolve()
    manifest = json.loads((path / "manifest.json").read_bytes())
    require(manifest["schema_version"] == "1", "Unsupported model bundle version")
    if expected_kind:
        require(manifest["kind"] == expected_kind, "Wrong model bundle kind")
    require(bool(manifest["files"]), "Model bundle has no files")
    for name, digest in manifest["files"].items():
        file = (path / name).resolve()
        require(file.parent == path, "Invalid model bundle member path")
        require(sha256(file.read_bytes()).hexdigest() == digest, "Model bundle checksum mismatch")
    return manifest


def load_model_records(path, kind):
    manifest = verify_model_bundle(path)
    require(kind in manifest["counts"], "Record kind is absent from this bundle")
    rows = pq.read_table(Path(path) / (kind + ".parquet")).to_pylist()
    for row in rows:
        for key in manifest["json_columns"].get(kind, []):
            if row[key] is not None:
                row[key] = json.loads(row[key])
        require(fingerprint({k: v for k, v in row.items() if k != "record_id"}) == row["record_id"],
                "Canonical model record identity mismatch")
    return rows


def persist_model_bundle(store, output, kind, contract, corpus, records, evidence):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        require(records and evidence, "A model/reference bundle needs authentic records and evidence")
        expected = {row["record_id"]: row for row in records}
        require(len(expected) == len(records), "Duplicate canonical records within a dataset")
        require(len({row["context_id"] for row in records}) == len(records),
                "Multiple active revisions of the same source context")
        for row in records:
            require(row["record_id"] == fingerprint({k: v for k, v in row.items() if k != "record_id"}),
                    "Canonical model record identity mismatch")
        assets = {asset["raw_sha256"]: asset for asset in corpus["assets"]}
        for asset in corpus["assets"]:
            checked_bytes(asset)
            require(asset["http_status"] == 200, "A failed response cannot supply model records")
        proof = {fingerprint(row): row for row in evidence}
        require(len(proof) == len(evidence), "Duplicate source evidence bindings")
        require({row["record_id"] for row in evidence} == expected.keys(), "Incomplete record lineage")
        require(all(row["source_asset_id"] in assets for row in evidence), "Unknown source evidence asset")
        primary = {}
        for row in evidence:
            if row["evidence_role"] == "value":
                primary.setdefault(row["record_id"], row["source_asset_id"])
        require(primary.keys() == expected.keys(), "Every record needs a primary value source")
        identifier = fingerprint({"kind": kind, "contract": contract,
                                  "records": sorted(expected), "evidence": sorted(proof)})
        store.migrate()
        with store.session() as connection:
            for asset in corpus["assets"]:
                connection.execute(
                    "INSERT INTO source_assets VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (asset["raw_sha256"], asset["raw_sha256"], asset["raw_path"], asset["response_url"],
                     asset["retrieved_at"], Jsonb(asset)),
                )
                previous = connection.execute(
                    "SELECT receipt FROM model_source_requests WHERE request_id=%s",
                    (asset["request_id"],),
                ).fetchone()
                require(not previous or previous[0] == asset, "Acquisition receipt changed in place")
                connection.execute(
                    "INSERT INTO model_source_requests VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    (asset["request_id"], asset["raw_sha256"], Jsonb(asset)),
                )
            connection.execute(
                "INSERT INTO model_datasets(dataset_id,manifest) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                (identifier, Jsonb({"kind": kind, "contract": contract, "corpus": corpus})),
            )
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO model_source_records VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    [(r["record_id"], r["context_id"], r["record_kind"], r["site_id"],
                      primary[r["record_id"]], Jsonb(r)) for r in records],
                )
                cursor.executemany(
                    "INSERT INTO model_dataset_records VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    [(identifier, row["record_id"]) for row in records],
                )
                cursor.executemany(
                    "INSERT INTO model_dataset_requests VALUES (%s,%s) ON CONFLICT DO NOTHING",
                    [(identifier, asset["request_id"]) for asset in corpus["assets"]],
                )
                cursor.executemany(
                    "INSERT INTO model_record_evidence VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    [(identifier, e["record_id"], e["source_asset_id"], e["source_locator"], e["evidence_role"])
                     for e in evidence],
                )
            readback = _read_records(connection, identifier)
            require({r["record_id"]: r for r in readback} == expected, "Stored model record conflict")
        with store.session(repeatable_read=True) as connection:
            restored = _read_records(connection, identifier)
            restored_evidence = [
                dict(zip(("record_id", "source_asset_id", "source_locator", "evidence_role"), row))
                for row in connection.execute(
                    "SELECT record_id,source_asset_id,source_locator,evidence_role FROM model_record_evidence "
                    "WHERE dataset_id=%s ORDER BY record_id,source_asset_id,source_locator,evidence_role",
                    (identifier,),
                ).fetchall()
            ]
        require({r["record_id"]: r for r in restored} == expected, "Independent SQL readback mismatch")
        require({fingerprint(row) for row in restored_evidence} == proof.keys(), "Source lineage readback mismatch")
        counts, json_columns = {}, {}
        for record_kind in sorted({row["record_kind"] for row in restored}):
            rows = [row for row in restored if row["record_kind"] == record_kind]
            nested = sorted({key for row in rows for key, value in row.items() if isinstance(value, (dict, list))})
            exported = [{key: json.dumps(value, sort_keys=True, allow_nan=False)
                         if key in nested and value is not None else value for key, value in row.items()}
                        for row in rows]
            file = output / (record_kind + ".parquet")
            pq.write_table(pa.Table.from_pylist(exported), file)
            require(pq.read_table(file).to_pylist() == exported, "Parquet model record roundtrip mismatch")
            counts[record_kind], json_columns[record_kind] = len(rows), nested
        pq.write_table(pa.Table.from_pylist(restored_evidence), output / "evidence.parquet")
        write_json(output / "corpus.json", corpus)
        manifest = {"schema_version": "1", "kind": kind, "dataset_id": identifier, "contract": contract,
                    "counts": counts, "json_columns": json_columns,
                    "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}}
        write_json(output / "manifest.json", manifest)
        return manifest
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(error).__name__})
        raise


def _read_records(connection, identifier):
    return [row[0] for row in connection.execute(
        "SELECT r.record FROM model_source_records r JOIN model_dataset_records d USING(record_id) "
        "WHERE d.dataset_id=%s ORDER BY r.record_id", (identifier,),
    ).fetchall()]
