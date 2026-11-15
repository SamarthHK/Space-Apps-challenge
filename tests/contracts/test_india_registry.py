"""Actual source identities remain distinct from crop-use training labels."""

import os
from pathlib import Path

import pytest
import yaml

from agri_data.contracts.india_cli import database_store
from agri_data.contracts.india_registry import build_india_registry
from agri_data.contracts.model_records import load_model_records, verify_model_bundle


ROOT = Path(__file__).resolve().parents[2]


def test_real_commodity_groups_and_taxa_are_not_silently_transferred():
    path = os.environ.get("AGRI_INDIA_REGISTRY")
    assert path, "Set AGRI_INDIA_REGISTRY to a built, source-linked Indian registry"
    verify_model_bundle(Path(path), "india_crop_registry")
    rows = {row["crop_use_id"]: row for row in load_model_records(path, "crop_registry")}
    mustard = rows["des:17"]
    assert mustard["display_name"] == "Rapeseed &Mustard"
    assert mustard["profile_link"]["profile_id"] == "548"
    assert mustard["profile_link"]["trait_feature_eligible"] is False
    assert rows["gaez:RSD"]["profile_link"] is None
    assert rows["gaez:BAN"]["profile_link"]["trait_feature_eligible"] is False
    assert rows["gaez:MZS"]["profile_link"]["trait_feature_eligible"] is False
    assert rows["gaez:MZE"]["profile_link"]["trait_feature_eligible"] is True
    assert rows["ecocrop:1112"]["display_name"] == "Fragaria x ananassa"
    assert all(not row["outcome_transfer_allowed"] for row in rows.values())
    assert all(row["presence_record_id"] for row in rows.values() if row["source_namespace"] == "des")


def test_real_registry_replays_and_rejects_a_different_taxon(tmp_path):
    profiles = os.environ.get("AGRI_INDIA_PROFILES")
    outcomes = os.environ.get("AGRI_INDIA_OUTCOMES")
    gaez = os.environ.get("AGRI_GAEZ_CORPUS")
    original = os.environ.get("AGRI_INDIA_REGISTRY")
    assert all((profiles, outcomes, gaez, original)), "Provide the authentic input bundles and GAEZ corpus"
    store = database_store(ROOT / "config" / "acceptance.yaml")
    config = ROOT / "config" / "india_model.yaml"
    replay = build_india_registry(config, profiles, outcomes, gaez, tmp_path / "replay", store)
    assert replay["dataset_id"] == verify_model_bundle(original)["dataset_id"]
    changed = yaml.safe_load(config.read_bytes())
    changed["crop_profile_links"]["1574"]["scientific_name"] = changed["crop_profile_links"]["2114"]["scientific_name"]
    wrong = tmp_path / "wrong-identity.yaml"
    wrong.write_text(yaml.safe_dump(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="different authentic plant identity"):
        build_india_registry(wrong, profiles, outcomes, gaez, tmp_path / "rejected", store)
