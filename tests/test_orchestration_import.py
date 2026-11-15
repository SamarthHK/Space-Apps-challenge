import json
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from agri_data.storage.models import Base, Observation, Project
from agri_data.storage.database import seed_metadata
from agri_data.geo.kml import load_kml
from agri_data.pipeline import orchestration


def test_import_repeat_run_preserves_count_and_text(tmp_path, monkeypatch):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_metadata(session)

    @contextmanager
    def session_factory():
        with Session(engine) as session:
            with session.begin():
                yield session

    monkeypatch.setattr(orchestration, "init_db", lambda: None)
    monkeypatch.setattr(orchestration, "get_db_session", session_factory)
    monkeypatch.setattr(orchestration.settings, "raw_dir", tmp_path / "raw")
    monkeypatch.setattr(orchestration.settings, "exports_dir", tmp_path / "exports")
    name = load_kml("data/input/farm_area.kml").iloc[0]["name"]
    (tmp_path / "samples.json").write_text('[{"variable_id":"aquifer","value_text":"granite"}]')
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"datasets": [{"id": "well", "source_id": "local_well", "domain": "water", "field_name": name, "path": "samples.json", "variables": {"aquifer": {"unit": "category", "description": "Formation"}}}]}))
    for _ in range(2):
        result = orchestration.run_pipeline("data/input/farm_area.kml", domains=[], import_plan=plan)
    with Session(engine) as session:
        assert session.query(Observation).count() == 1
        observation = session.query(Observation).one()
        assert observation.value_text == "granite"
        assert observation.observed_at is None
        assert observation.source_asset_id is not None
        assert session.query(Project).count() == 1
    profile = next(p for p in result["profiles"].values() if p["field"]["name"] == name)
    assert profile["complete_observations"]["row_count"] == 1
