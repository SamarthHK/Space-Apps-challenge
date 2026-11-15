"""Canonical preparation regressions against the actual archived evidence."""

import os

import psycopg
from psycopg import sql
import pytest

from agri_data.api.data import DataSettings, DataStore
from agri_data.contracts.canonical import canonical_record, register_canonical
from agri_data.contracts.identity import fingerprint
from agri_data.contracts.observation import Observation
from agri_data.contracts.postgres import PostgresStore


@pytest.fixture
def prepared():
    settings = DataSettings.from_env({
        key.replace("AGRI_TEST_", "AGRI_API_"): value
        for key, value in os.environ.items() if key.startswith("AGRI_TEST_")
    })
    assert settings and DataStore(settings).available(), "Configure authentic prepared PostgreSQL"
    return settings


def test_repeated_source_evidence_has_one_canonical_identity(prepared):
    with DataStore(prepared).session() as connection:
        rows = connection.execute(
            "SELECT c.canonical_observation_id,c.field_id,c.scientific_record,o.record "
            "FROM canonical_observations c JOIN canonical_fields f USING(field_id) "
            "JOIN observation_evidence e USING(canonical_observation_id) "
            "JOIN observations o USING(observation_id) "
            "WHERE f.project_id=ANY(%s) ORDER BY c.canonical_observation_id,o.observation_id LIMIT 20",
            (list(prepared.project_ids),),
        ).fetchall()
    assert rows
    identifiers = []
    for identifier, field_id, scientific, record in rows:
        rebuilt = canonical_record(record, field_id, scientific["source_context"])
        assert rebuilt == scientific
        assert fingerprint(rebuilt) == identifier
        identifiers.append(identifier)
    assert len(set(identifiers)) < len(identifiers), "Repeated authentic receipts are required"


def test_repeat_registration_and_receipt_readback_are_idempotent(prepared):
    store = PostgresStore(prepared.database, prepared.user, prepared.schema,
                          connection_env="AGRI_TEST_DATABASE_URL")
    with psycopg.connect(prepared.dsn) as connection:
        with connection.transaction(force_rollback=True):
            connection.execute(sql.SQL("SET LOCAL search_path TO {},public").format(
                sql.Identifier(prepared.schema)))
            identifier, scientific, record = connection.execute(
                "SELECT c.canonical_observation_id,c.scientific_record,o.record "
                "FROM canonical_observations c JOIN canonical_fields f USING(field_id) "
                "JOIN observation_evidence e USING(canonical_observation_id) "
                "JOIN observations o USING(observation_id) "
                "WHERE f.project_id=ANY(%s) LIMIT 1", (list(prepared.project_ids),),
            ).fetchone()
            before = connection.execute(
                "SELECT (SELECT count(*) FROM canonical_observations),"
                "(SELECT count(*) FROM observation_evidence)"
            ).fetchone()
            assert register_canonical(connection, record, scientific["source_context"]) == identifier
            observation = Observation.model_validate(record)
            assert store.save_observation(connection, observation) is False
            assert connection.execute(
                "SELECT (SELECT count(*) FROM canonical_observations),"
                "(SELECT count(*) FROM observation_evidence)"
            ).fetchone() == before
    assert any(row.observation_id == observation.observation_id
               for row in store.read_observations(observation.extraction_job_id))
