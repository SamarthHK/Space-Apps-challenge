"""Source-qualified crop/use links; statistical groups never become child-crop labels."""

import json
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from .gaez import catalogue_selection
from .model_records import load_model_records, model_record, persist_model_bundle, source_evidence, verify_model_bundle
from .storage_proof import require


def build_india_registry(config_path, profile_bundle, outcome_bundle, gaez_corpus, output, store):
    config = yaml.safe_load(Path(config_path).read_bytes())
    manifests = [verify_model_bundle(profile_bundle, "crop_requirement_dataset"),
                 verify_model_bundle(outcome_bundle, "india_regional_outcome_dataset")]
    profiles = {row["source_crop_id"]: row for row in load_model_records(profile_bundle, "crop_profile")}
    outcomes = load_model_records(outcome_bundle, "regional_outcome")
    acquired = json.loads(Path(gaez_corpus).read_bytes())
    require(acquired["kind"] == "gaez_reference_corpus" and acquired["status"] == "complete", "GAEZ source capture is incomplete")
    _, crops, _ = catalogue_selection(acquired["catalogue"], acquired["specification"])
    source_corpora = [json.loads((Path(path) / "corpus.json").read_bytes()) for path in (profile_bundle, outcome_bundle)]
    assets = {asset["raw_sha256"]: asset for corpus in [*source_corpora, acquired] for asset in corpus["assets"]}
    bindings = {}
    for path in (profile_bundle, outcome_bundle):
        for proof in pq.read_table(Path(path) / "evidence.parquet").to_pylist():
            if proof["evidence_role"] == "value":
                bindings.setdefault(proof["record_id"], proof)
    observed = {}
    for row in outcomes:
        if row["area"] is not None and row["area"] > 0:
            previous = observed.setdefault(row["source_crop_id"], row)
            require(previous["crop_name"] == row["crop_name"], "Ambiguous Indian commodity identity")
    links = {}
    for profile_id, spec in config["crop_profile_links"].items():
        require(profile_id in profiles and profiles[profile_id]["scientific_name"] == spec["scientific_name"],
                "Crosswalk is bound to a different authentic plant identity")
        for namespace, catalogue in (("gaez", crops), ("des", observed)):
            for code in spec.get(namespace, []):
                require(code in catalogue, "Crosswalk references an absent source crop")
                key = f"{namespace}:{code}"
                require(key not in links, "Multiple profiles require an explicitly grouped crosswalk")
                links[key] = {"profile_id": profile_id,
                              "trait_feature_eligible": namespace == "gaez" and code in spec.get("trait_eligible_gaez", []),
                              "relation": "qualified_crop_reference" if namespace == "gaez" and
                              code in spec.get("trait_eligible_gaez", []) else "partial_or_broader_reference"}
    entries = [("gaez", code, crop["name"], None) for code, crop in crops.items()]
    entries += [("des", code, row["crop_name"], row) for code, row in observed.items()]
    entries += [("ecocrop", code, row["scientific_name"], None) for code, row in profiles.items()]
    records, evidence = [], []
    for namespace, code, name, outcome in entries:
        key = f"{namespace}:{code}"
        link = links.get(key)
        record = model_record("crop_registry", ["india_crop_registry", key], {
            "crop_use_id": key, "source_namespace": namespace, "source_crop_id": code, "display_name": name,
            "profile_link": link, "outcome_transfer_allowed": False,
            "indian_presence": "reported_positive_commodity_area" if outcome else "not_established_by_this_record",
            "presence_record_id": outcome["record_id"] if outcome else None,
            "presence_reporting_year": outcome["source_year_label"] if outcome else None,
            "training_support": "must_be_checked_per_task_and_split",
            "system_scope": "source_crop_or_use" if namespace == "gaez" else
            "reported_statistical_commodity" if namespace == "des" else "global_taxon_reference",
        })
        records.append(record)
        if namespace == "gaez":
            evidence.append(source_evidence(record, acquired["catalogue"], f"CODES_CROP:{code}"))
        else:
            proof = bindings[(outcome if namespace == "des" else profiles[code])["record_id"]]
            evidence.append(source_evidence(record, assets[proof["source_asset_id"]], proof["source_locator"]))
        if link:
            proof = bindings[profiles[link["profile_id"]]["record_id"]]
            evidence.append(source_evidence(record, assets[proof["source_asset_id"]], proof["source_locator"], "definition"))
    used = {proof["source_asset_id"] for proof in evidence}
    corpus = {"schema_version": "1", "kind": "india_crop_registry_corpus",
              "source_dataset_ids": [manifest["dataset_id"] for manifest in manifests],
              "assets": [asset for key, asset in assets.items() if key in used]}
    return persist_model_bundle(store, output, "india_crop_registry", {
        "schema_version": "1", "links": config["crop_profile_links"],
        "aggregate_outcome_relabelling": False, "global_reference_is_indian_presence": False,
        "absent_trait_policy": "missing_not_substituted", "unseen_crop_predictions": False,
    }, corpus, records, evidence)
