"""Lossless evidence reconciliation, not automatic scientific acceptance.

Source-normalized records and receipts are retained. Only the canonical view
collapses repeated scientific content. Distinct revisions share a context ID.
"""

from hashlib import sha256
from pathlib import Path
import json

from psycopg.types.json import Jsonb

from .identity import fingerprint, stable_field_id
from .corpus import COLLECTION
from .observation import Observation


AUDIT_FIELDS = {
    "observation_id", "source_asset_id", "extraction_job_id", "retrieved_at",
    "created_at", "raw_sha256", "validation_status",
}
VALUE_FIELDS = {
    "value_numeric", "value_text", "value_boolean", "value_date", "value_geometry",
    "value_series_ref", "original_value", "quality_flags", "uncertainty",
    "uncertainty_unit", "uncertainty_method", "censoring_qualifier", "detection_limit",
}


def canonical_record(record, field_id, source_context):
    record = Observation.model_validate(record).model_dump(mode="json")
    scientific = {key: value for key, value in record.items() if key not in AUDIT_FIELDS}
    if field_id is not None:
        if scientific["subject_id"] == scientific["field_id"]:
            scientific["subject_id"] = field_id
        scientific["field_id"] = field_id
    scientific["source_context"] = source_context
    # POWER daily precipitation is a mean rate over one provider-local day.
    # Do not generalize this identity conversion to subdaily or other products.
    if (record["source_id"] == "SRC-004" and record["variable_id"] == "daily_rainfall"
            and record["temporal_resolution"] == "daily"
            and record["standardized_unit"] == "mm/day"):
        scientific["standardized_unit"] = "mm"
        scientific["normalization"] = {
            "method": "daily_mean_rate_times_one_day", "formula": "mm/day * 1 day = mm",
            "reference": "NASA POWER daily response header and PRECTOTCORR parameter metadata",
        }
    return scientific


def register_canonical(connection, record, source_context):
    field_id = record["field_id"]
    if field_id:
        alias = connection.execute(
            "SELECT canonical_field_id FROM field_aliases WHERE alias_field_id=%s", (field_id,)
        ).fetchone()
        field_id = alias[0] if alias else field_id
    scientific = canonical_record(record, field_id, source_context)
    context = {key: value for key, value in scientific.items() if key not in VALUE_FIELDS}
    identifier = fingerprint(scientific)
    connection.execute(
        "INSERT INTO canonical_observations "
        "(canonical_observation_id,context_id,field_id,variable_id,scientific_record) "
        "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (identifier, fingerprint(context), field_id, record["variable_id"], Jsonb(scientific)),
    )
    prior = connection.execute(
        "SELECT canonical_observation_id FROM observation_evidence WHERE observation_id=%s",
        (record["observation_id"],),
    ).fetchone()
    if prior and prior[0] != identifier:
        raise ValueError("Evidence already has a different canonical mapping; explicit version migration required")
    connection.execute(
        "INSERT INTO observation_evidence VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (record["observation_id"], identifier, record["source_asset_id"],
         record["extraction_job_id"], record["source_record_locator"]),
    )
    return identifier


def reconcile_reference(store, corpus_path):
    """Map only the explicitly identified official parcel; never merge by overlap alone."""
    corpus = json.loads(corpus_path.read_bytes())
    asset = corpus["parcel_asset"]
    payload = Path(asset["raw_path"]).read_bytes()
    if sha256(payload).hexdigest() != asset["raw_sha256"]:
        raise ValueError("Official parcel asset changed")
    parcel = json.loads(payload)
    if parcel["id"] != corpus["parcel_id"]:
        raise ValueError("Parcel identity mismatch")
    canonical_id = stable_field_id("public_reference", COLLECTION, parcel["id"])
    legacy_id = "PDOK_" + parcel["id"]
    store.migrate()
    with store.session() as connection:
        connection.execute("SELECT pg_advisory_xact_lock(hashtext('canonical-reconciliation'))")
        existing = connection.execute(
            "SELECT project_id,source_identifier FROM fields WHERE field_id=%s", (canonical_id,)
        ).fetchone()
        if not existing:
            raise ValueError("Import the authentic boundary before reconciling its weather records")
        old = connection.execute(
            "SELECT project_id,source_identifier FROM fields WHERE field_id=%s", (legacy_id,)
        ).fetchone()
        if old:
            if old != ("public_reference", parcel["id"]):
                raise ValueError("Legacy provider identity does not match the reviewed reference")
            same = connection.execute(
                "SELECT EXISTS(SELECT 1 FROM field_boundaries a JOIN field_boundaries b "
                "ON ST_Equals(a.geometry,b.geometry) WHERE a.field_id=%s AND b.field_id=%s)",
                (legacy_id, canonical_id),
            ).fetchone()[0]
            if not same:
                raise ValueError("Reference boundaries disagree; do not infer an alias")
            connection.execute(
                "INSERT INTO field_aliases VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (legacy_id, canonical_id, Jsonb({
                    "provider_id": parcel["id"], "parcel_sha256": asset["raw_sha256"],
                    "method": "explicit provider ID and independent PostGIS geometry equality",
                })),
            )
        rows = connection.execute(
            "SELECT o.record,a.path,a.raw_sha256 FROM observations o "
            "JOIN source_assets a USING(source_asset_id) WHERE o.source_id='SRC-004' "
            "AND o.field_id IN (%s,%s) ORDER BY o.observation_id", (legacy_id, canonical_id),
        ).fetchall()
        contexts = {}
        for record, path, digest in rows:
            if digest not in contexts:
                raw_bytes = Path(path).read_bytes()
                if sha256(raw_bytes).hexdigest() != digest:
                    raise ValueError("Weather evidence checksum mismatch")
                raw = json.loads(raw_bytes)
                contexts[digest] = {
                    "geometry": raw["geometry"], "sources": raw["header"]["sources"],
                    "api": raw["header"]["api"], "time_standard": raw["header"]["time_standard"],
                    "parameters": raw["parameters"],
                }
            register_canonical(connection, record, contexts[digest])
        counts = connection.execute(
            "SELECT (SELECT count(*) FROM observations),"
            "(SELECT count(*) FROM canonical_observations),"
            "(SELECT count(*) FROM observation_evidence),"
            "(SELECT count(*) FROM canonical_fields),"
            "(SELECT count(*) FROM accepted_canonical_observations)"
        ).fetchone()
    return dict(zip(("source_observations", "canonical_observations", "evidence_links",
                     "canonical_fields", "accepted_canonical_observations"), counts))
