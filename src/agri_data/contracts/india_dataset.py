"""Source-linked reference features and spatially isolated, crop-covered evaluation."""

from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from psycopg.types.json import Jsonb
import yaml

from .identity import fingerprint
from .model_records import load_model_records, verify_model_bundle
from .outcome_data import write_json
from .storage_proof import require


TASK = "india_published_reference_suitability"
TRAIT_METRICS = ("temperature", "annual_water", "soil_ph", "altitude")
TRAIT_BOUNDS = ("optimal_min", "optimal_max", "absolute_min", "absolute_max")


def verify_reference_dataset(path):
    manifest = verify_model_bundle(path, "india_reference_training_dataset")
    require(manifest["task"] == TASK and manifest["target"]["divisor"] == 10000,
            "Unsupported reference training target")
    return manifest


def validate_splits(examples, membership, folds, minimum_groups):
    require(not examples["example_id"].duplicated().any(), "Duplicate reference example")
    require(not membership["site_id"].duplicated().any(), "A native cell has multiple split memberships")
    require(set(examples["site_id"]) <= set(membership["site_id"]), "Example is absent from split membership")
    require(membership.groupby("spatial_group")["partition"].nunique().max() == 1,
            "A spatial group crosses evaluation partitions")
    require(membership.groupby("spatial_group")["fold"].nunique().max() == 1,
            "A spatial group crosses development folds")
    require(set(membership["partition"]) == {"development", "calibration", "test"},
            "Development, calibration and locked test must all be populated")
    require(set(membership.loc[membership.partition == "development", "fold"]) == set(range(folds)),
            "Every declared development fold needs spatial groups")
    frame = examples.merge(membership, on="site_id", validate="many_to_one")
    require(np.isfinite(frame.target).all() and frame.target.between(0, 1).all(),
            "Non-finite or out-of-range reference target")
    keys = ["crop_id", "production_system"]
    development = frame[frame.partition == "development"]

    def coverage(train, held_out):
        supported = set(map(tuple, train[keys].drop_duplicates().to_numpy()))
        needed = set(map(tuple, held_out[keys].drop_duplicates().to_numpy()))
        require(needed <= supported, "Held-out crop/system has no target-bearing training support")
        groups = train.groupby(keys)["spatial_group"].nunique()
        require(len(groups) and int(groups.min()) >= minimum_groups,
                "Insufficient independent training spatial groups per crop/system")

    coverage(development, frame[frame.partition != "development"])
    for fold in range(folds):
        coverage(development[development.fold != fold], development[development.fold == fold])
    return frame


def _spatial_membership(sites, contexts, specification):
    step = specification["spatial_block_degrees"]
    require(step > 0, "Spatial block size must be positive")
    blocks = {row["site_id"]: f"{math.floor(row['longitude'] / step)}:{math.floor(row['latitude'] / step)}"
              for row in sites}
    parent = {block: block for block in blocks.values()}

    def root(block):
        while parent[block] != block:
            parent[block] = parent[parent[block]]
            block = parent[block]
        return block

    support_blocks = {}
    for context in contexts:
        block = blocks[context["site_id"]]
        for support in json.loads(context["nasa_support_ids"]):
            previous = support_blocks.setdefault(support, block)
            a, b = sorted((root(block), root(previous)))
            parent[b] = a
    groups = sorted({root(block) for block in blocks.values()},
                    key=lambda group: fingerprint([specification["seed"], group]))
    test_count = max(1, math.ceil(len(groups) * specification["test_fraction"]))
    calibration_count = max(1, math.ceil(len(groups) * specification["calibration_fraction"]))
    require(len(groups) - test_count - calibration_count >= specification["development_folds"] * 2,
            "Too few independent spatial groups for the declared evaluation")
    assignments = {}
    for index, group in enumerate(groups):
        if index < test_count:
            assignments[group] = ("test", -1)
        elif index < test_count + calibration_count:
            assignments[group] = ("calibration", -1)
        else:
            assignments[group] = ("development", (index - test_count - calibration_count) %
                                   specification["development_folds"])
    return pd.DataFrame([{"site_id": site, "native_block": block, "spatial_group": root(block),
                          "partition": assignments[root(block)][0], "fold": assignments[root(block)][1]}
                         for site, block in sorted(blocks.items())])


def _nasa_lookup(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["metric_id"], row["period_id"])].append(row)
    result = {}
    for key, values in grouped.items():
        values.sort(key=lambda row: (row["longitude"], row["latitude"]))
        spacing = values[0]["source_grid_spacing_degrees"]
        require(all(row["source_grid_spacing_degrees"] == spacing for row in values),
                "NASA native spacing changes inside a requested metric/period")
        positions = np.array([[row["longitude"], row["latitude"]] for row in values])
        result[key] = values, positions, np.array(spacing)
    return result


def _matched_nasa(lookup, metric, period, site, start, end):
    if (metric, period) not in lookup:
        return None, "period_not_acquired"
    rows, positions, spacing = lookup[(metric, period)]
    distance = np.abs(positions - [site["longitude"], site["latitude"]]) / spacing
    matches = np.flatnonzero((distance <= 0.5 + 1e-10).all(axis=1))
    if not len(matches):
        return None, "no_native_footprint_at_reference_center"
    index = min(matches, key=lambda i: (float(np.square(distance[i]).sum()), int(i)))
    row = rows[index]
    require(row["window_start"] == start and row["window_end"] == end,
            "NASA feature and target periods differ")
    require(row["temporal_support"] == "complete_monthly_history_derived_normal",
            "NASA support is not the declared historical normal")
    return row, row["availability"]


def build_reference_dataset(config_path, gaez_path, nasa_path, registry_path, profiles_path, output, store):
    paths = {"gaez": Path(gaez_path), "nasa": Path(nasa_path),
             "registry": Path(registry_path), "profiles": Path(profiles_path)}
    kinds = {"gaez": "india_gaez_reference_dataset", "nasa": "india_nasa_reference_dataset",
             "registry": "india_crop_registry", "profiles": "crop_requirement_dataset"}
    manifests = {key: verify_model_bundle(path, kinds[key]) for key, path in paths.items()}
    config = yaml.safe_load(Path(config_path).read_bytes())
    specification = config["reference_training"]
    require(0 < specification["test_fraction"] < 0.5 and
            0 < specification["calibration_fraction"] < 0.5, "Invalid held-out fractions")
    sites = load_model_records(gaez_path, "spatial_support")
    climate = load_model_records(gaez_path, "climate_normal")
    static = load_model_records(gaez_path, "environment_reference")
    targets = load_model_records(gaez_path, "crop_suitability")
    profiles = load_model_records(gaez_path, "crop_profile")
    registry = {row["crop_use_id"]: row for row in load_model_records(registry_path, "crop_registry")}
    traits = load_model_records(profiles_path, "crop_requirement")
    nasa = load_model_records(nasa_path, "climate_normal")
    periods = manifests["gaez"]["contract"]["periods"]
    require(periods == manifests["nasa"]["contract"]["periods"], "Reference period definitions differ")
    features, source_ids = {}, set()

    def feature(name, group, dtype, unit, support):
        definition = {"group": group, "dtype": dtype, "unit": unit, "temporal_support": support}
        require(name not in features or features[name] == definition, "Feature unit or support changed")
        features[name] = definition

    def bind(mapping, name, row):
        mapping[name] = row["record_id"]
        source_ids.add(row["record_id"])

    weather = {}
    for row in climate:
        key = row["site_id"], row["period_id"], row["metric_id"]
        require(key not in weather, "Repeated climate feature at one context")
        weather[key] = row
    terrain = {(row["site_id"], row["metric_id"]): row for row in static}
    require(len(terrain) == len(static), "Repeated static feature at one site")
    nasa_lookup = _nasa_lookup(nasa)
    contexts, context_ids = [], {}
    for site in sorted(sites, key=lambda row: row["site_id"]):
        for period, (start, end) in sorted(periods.items()):
            start, end = f"{start}-01-01", f"{end}-12-31"
            values = {"site_id": site["site_id"], "period_id": period, "analysis_start": start,
                      "analysis_end": end, "mode": "historical_reference_analysis",
                      "latitude": site["latitude"], "longitude": site["longitude"]}
            lineage, availability, supports = {}, {}, set()
            for name in ("latitude", "longitude"):
                feature(name, "geography", "numeric", "degree", "versioned_static_reference")
                bind(lineage, name, site)
            for metric in manifests["gaez"]["contract"]["climate_variables"]:
                row = weather[(site["site_id"], period, metric)]
                require(row["window_start"] == start and row["window_end"] == end and
                        row["scenario"] == "HIST" and row["climate_source"] == "AGERA5",
                        "GAEZ feature and target temporal/scenario support differ")
                name = "gaez_" + metric
                values[name] = row["value"]
                availability[name] = row["availability"]
                feature(name, "gaez_climate", "numeric", row["unit"], row["temporal_support"])
                bind(lineage, name, row)
            for metric in manifests["gaez"]["contract"]["static_variables"]:
                row = terrain[(site["site_id"], metric)]
                require(not row["historical_measurement"], "Static reference relabelled as a historical soil test")
                name = "static_" + metric
                categorical = row["value_type"] == "category"
                values[name] = row["value_text"] if categorical else row["value"]
                availability[name] = row["availability"]
                feature(name, "soil_terrain", "categorical" if categorical else "numeric",
                        row["unit"], row["temporal_support"])
                bind(lineage, name, row)
            for metric in sorted(manifests["nasa"]["contract"]["parameters"]):
                name = "nasa_" + metric
                row, status = _matched_nasa(nasa_lookup, metric, period, site, start, end)
                values[name], availability[name] = row["value"] if row else None, status
                definition = next(item for item in nasa if item["metric_id"] == metric)
                feature(name, "nasa_climate", "numeric", definition["unit"],
                        "complete_monthly_history_derived_normal")
                if row:
                    bind(lineage, name, row)
                    supports.add(row["site_id"])
            values["source_record_ids"] = json.dumps(lineage, sort_keys=True)
            values["availability"] = json.dumps(availability, sort_keys=True)
            values["nasa_support_ids"] = json.dumps(sorted(supports))
            values["context_id"] = fingerprint(values)
            context_ids[(site["site_id"], period)] = values["context_id"]
            contexts.append(values)
    trait_lookup = {(row["source_crop_id"], row["metric_id"]): row for row in traits}
    crops = []
    for profile in sorted(profiles, key=lambda row: row["source_crop_id"]):
        crop = "gaez:" + profile["source_crop_id"]
        entry = registry[crop]
        require(entry["display_name"] == profile["source_name"], "Registry/GAEZ crop identity differs")
        values = {"crop_id": crop, "display_name": entry["display_name"], "crop_group": profile["crop_group"],
                  "registry_record_id": entry["record_id"], "profile_record_id": profile["record_id"]}
        source_ids.update((entry["record_id"], profile["record_id"]))
        lineage = {}
        link = entry["profile_link"]
        for metric in TRAIT_METRICS:
            row = trait_lookup.get((link["profile_id"], metric)) if link and link["trait_feature_eligible"] else None
            definition = next(item for item in traits if item["metric_id"] == metric)
            for bound in TRAIT_BOUNDS:
                name = f"trait_{metric}_{bound}"
                values[name] = row[bound] if row else None
                feature(name, "crop_traits", "numeric", definition["unit"], definition["temporal_support"])
                if row:
                    bind(lineage, name, row)
        values["source_record_ids"] = json.dumps(lineage, sort_keys=True)
        crops.append(values)
    feature("crop_id", "crop_identity", "categorical", "source_crop_or_use", "reference")
    feature("production_system", "management", "categorical", "source_water_input_regime", "reference")
    crop_ids = {crop["crop_id"] for crop in crops}
    examples = []
    for target in targets:
        crop = "gaez:" + target["source_crop_id"]
        require(crop in crop_ids and target["unit"] == "Index" and target["metric_id"] == "RES05-SXX" and
                target["evidence_type"] == "modelled_product" and target["scenario"] == "HIST" and
                target["climate_source"] == "AGERA5", "Incompatible or unsupported reference target")
        start, end = periods[target["period_id"]]
        require(target["window_start"] == f"{start}-01-01" and target["window_end"] == f"{end}-12-31",
                "Target and feature periods differ")
        require(0 <= target["value"] <= 10000, "Invalid published reference score")
        body = {"target_record_id": target["record_id"],
                "context_id": context_ids[(target["site_id"], target["period_id"])],
                "site_id": target["site_id"], "crop_id": crop, "production_system": target["production_system"],
                "target": target["value"] / 10000}
        examples.append({"example_id": fingerprint(body), **body})
        source_ids.add(target["record_id"])
    examples = pd.DataFrame(examples).sort_values("example_id").reset_index(drop=True)
    membership = _spatial_membership(sites, contexts, specification)
    joined = validate_splits(examples, membership, specification["development_folds"],
                             specification["minimum_training_groups"])
    support_splits = {}
    for context in contexts:
        membership_row = membership.set_index("site_id").loc[context["site_id"]]
        assignment = (membership_row["partition"], int(membership_row["fold"]))
        for support in json.loads(context["nasa_support_ids"]):
            require(support_splits.setdefault(support, assignment) == assignment,
                    "A coarse NASA source footprint crosses held-out partitions")
    inputs = {role: {"path": str(path.resolve()), "dataset_id": manifests[role]["dataset_id"],
                     "manifest_sha256": sha256((path / "manifest.json").read_bytes()).hexdigest()}
              for role, path in paths.items()}
    manifest = {
        "schema_version": "1", "kind": "india_reference_training_dataset", "task": TASK,
        "inputs": inputs, "split_specification": specification, "features": features, "periods": periods,
        "target": {"source": "GAEZ v5 RES05-SXX", "unit": "normalized_reference_index",
                   "divisor": 10000, "observed_success_probability": False},
        "spatial_join": "native_NASA_footprint_containing_GAEZ_cell_center_no_interpolation",
        "shared_footprints_grouped": True, "strict_as_of_supported": False,
        "preplant_supported": False, "rotation_effects_supported": False,
        "perennial_establishment_supported": False,
        "counts": {"examples": len(examples), "contexts": len(contexts), "crops": len(crops),
                   "sites": len(membership), "spatial_groups": int(membership.spatial_group.nunique())},
        "partition_rows": {str(k): int(v) for k, v in joined.partition.value_counts().items()},
        "missing_requirement_axes": ["dated_field_soil_pH", "soil_depth_drainage_salinity_measurements",
                                     "nutrient_SOC_measurements", "current_soil_moisture",
                                     "planting_calendar", "cultivar_phenology_age", "field_rotation_history"],
        "attribution": ["FAO and IIASA, GAEZ v5 (2025), CC-BY-4.0.",
                        "FAO EcoCrop published crop requirements.",
                        "NASA POWER Project, NASA Langley Research Center.",
                        "geoBoundaries India ADM0 reference mask (2014), CC0."],
    }
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        pd.DataFrame(contexts).to_parquet(output / "contexts.parquet", index=False)
        pd.DataFrame(crops).to_parquet(output / "crops.parquet", index=False)
        examples.to_parquet(output / "examples.parquet", index=False)
        membership.to_parquet(output / "split_membership.parquet", index=False)
        manifest["files"] = {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())}
        manifest["dataset_id"] = fingerprint({key: value for key, value in manifest.items() if key != "inputs"} |
                                              {"input_ids": {k: v["dataset_id"] for k, v in inputs.items()}})
        store.migrate()
        with store.session() as connection:
            connection.execute("INSERT INTO model_datasets(dataset_id,manifest) VALUES (%s,%s) ON CONFLICT DO NOTHING",
                               (manifest["dataset_id"], Jsonb(manifest)))
            with connection.cursor() as cursor:
                cursor.executemany("INSERT INTO model_dataset_records VALUES (%s,%s) ON CONFLICT DO NOTHING",
                                   [(manifest["dataset_id"], record) for record in sorted(source_ids)])
        with store.session(repeatable_read=True) as connection:
            restored = connection.execute("SELECT manifest FROM model_datasets WHERE dataset_id=%s",
                                          (manifest["dataset_id"],)).fetchone()[0]
            stored_ids = {row[0] for row in connection.execute(
                "SELECT record_id FROM model_dataset_records WHERE dataset_id=%s", (manifest["dataset_id"],))}
        require(restored == manifest and stored_ids == source_ids, "Training manifest or source membership SQL mismatch")
        write_json(output / "manifest.json", manifest)
        verify_reference_dataset(output)
        return manifest
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(error).__name__})
        raise


def load_reference_frames(path):
    manifest = verify_reference_dataset(path)
    path = Path(path)
    examples = pd.read_parquet(path / "examples.parquet")
    membership = pd.read_parquet(path / "split_membership.parquet")
    specification = manifest["split_specification"]
    frame = validate_splits(examples, membership, specification["development_folds"],
                            specification["minimum_training_groups"])
    contexts = pd.read_parquet(path / "contexts.parquet")
    crops = pd.read_parquet(path / "crops.parquet")
    context_columns = [name for name in manifest["features"] if name in contexts]
    crop_columns = [name for name in manifest["features"] if name in crops and name != "crop_id"]
    frame = frame.merge(contexts[["context_id", "period_id", *context_columns]], on="context_id", validate="many_to_one")
    frame = frame.merge(crops[["crop_id", "crop_group", *crop_columns]], on="crop_id", validate="many_to_one")
    require(len(frame) == len(examples), "Feature join lost authentic target examples")
    return manifest, frame
