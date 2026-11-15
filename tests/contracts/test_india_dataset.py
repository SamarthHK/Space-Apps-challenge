"""Real reference joins, immutable holdouts and unseen-crop refusal."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

from agri_data.contracts.india_dataset import load_reference_frames, validate_splits
from agri_data.contracts.model_records import load_model_records


@pytest.fixture(scope="module")
def dataset():
    path = os.environ.get("AGRI_INDIA_DATASET")
    assert path, "Set AGRI_INDIA_DATASET to the built authentic reference cohort"
    manifest, frame = load_reference_frames(path)
    return Path(path), manifest, frame


def test_actual_native_cells_and_coarse_nasa_supports_do_not_leak(dataset):
    path, manifest, frame = dataset
    contexts = pd.read_parquet(path / "contexts.parquet")
    splits = pd.read_parquet(path / "split_membership.parquet").set_index("site_id")
    assignment = {}
    for row in contexts.to_dict("records"):
        scope = tuple(splits.loc[row["site_id"], ["partition", "fold"]])
        for support in json.loads(row["nasa_support_ids"]):
            assert assignment.setdefault(support, scope) == scope
    assert frame.groupby("site_id").partition.nunique().max() == 1
    assert frame.crop_id.nunique() == manifest["counts"]["crops"]
    assert len(contexts) < len(frame)


def test_real_target_and_time_joins_preserve_values_and_missing_period(dataset):
    path, manifest, frame = dataset
    reference = load_model_records(manifest["inputs"]["gaez"]["path"], "crop_suitability")
    first = reference[0]
    example = frame.loc[frame.target_record_id == first["record_id"]].iloc[0]
    assert example.target * 10000 == pytest.approx(first["value"])
    assert example.period_id == first["period_id"]
    assert example.crop_id == "gaez:" + first["source_crop_id"]
    earlier = frame.loc[frame.period_id == "HP8100", "nasa_ALLSKY_SFC_SW_DWN"]
    assert earlier.isna().all()
    assert frame.loc[frame.period_id == "HP0120", "nasa_ALLSKY_SFC_SW_DWN"].notna().any()
    crops = pd.read_parquet(path / "crops.parquet").set_index("crop_id")
    trait_columns = [name for name in crops if name.startswith("trait_")]
    assert crops.loc["gaez:BAN", trait_columns].isna().all()
    assert crops.loc["gaez:MZE", trait_columns].notna().any()


def test_real_held_out_crop_without_training_targets_is_rejected(dataset):
    path, manifest, _ = dataset
    examples = pd.read_parquet(path / "examples.parquet")
    membership = pd.read_parquet(path / "split_membership.parquet")
    development = set(membership.loc[membership.partition == "development", "site_id"])
    crop = examples.iloc[0].crop_id
    incomplete = examples.loc[~((examples.crop_id == crop) & examples.site_id.isin(development))]
    spec = manifest["split_specification"]
    with pytest.raises(ValueError, match="no target-bearing training support"):
        validate_splits(incomplete, membership, spec["development_folds"], spec["minimum_training_groups"])


def test_full_source_view_and_sql_membership_rebuild_identically(dataset, tmp_path):
    _, manifest, _ = dataset
    root = Path(__file__).resolve().parents[2]
    command = [sys.executable, "-m", "agri_data", "build-india-dataset",
               "--contract", str(root / "config" / "india_model.yaml"),
               "--config", str(root / "config" / "acceptance.yaml"), "--output", str(tmp_path / "replay")]
    for role in ("gaez", "nasa", "registry", "profiles"):
        command.extend(["--" + role, manifest["inputs"][role]["path"]])
    process = subprocess.run(command, cwd=root, capture_output=True, text=True)
    assert process.returncode == 0, process.stdout + process.stderr
    replay = json.loads(process.stdout)
    assert replay["dataset_id"] == manifest["dataset_id"]
    assert replay["files"] == manifest["files"]
