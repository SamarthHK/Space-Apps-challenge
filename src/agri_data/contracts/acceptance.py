"""Fail-closed S01 preparation and machine-readable gate reporting.

This is not a connection or scientific acceptance runner. Until the complete
atomic registry and authentic corpus exist, every acceptance suite is blocked.
"""

from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import json
import os
import uuid

import yaml

from .inventory import extract_inventory, legacy_audit
from .observation import Observation


def _timestamp():
    return datetime.now(timezone.utc).isoformat()


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _inspect_corpus(config, repository):
    evidence, blockers = [], []
    corpus = config.get("acceptance_corpus", {})
    for kind in (
        "boundaries", "crops_and_cultivars", "seasons", "source_records", "spatial_assets",
        "independent_references", "laboratory_reports", "device_exports",
    ):
        entries = corpus.get(kind, [])
        if not isinstance(entries, list):
            raise ValueError(f"acceptance_corpus.{kind} must be a list")
        if not entries:
            blockers.append({
                "id": f"S01-CORPUS-{kind}",
                "dependency": f"acceptance_corpus.{kind}",
                "reason": "No authentic evidence has been declared.",
                "attempted_route": "Read the configured acceptance corpus; no default sample is permitted.",
                "next_action": "Supply actual provenance-bearing records/references and freeze their acceptance contexts.",
            })
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("path") or not entry.get("origin"):
                raise ValueError(f"{kind}: every artifact needs path and origin")
            path = (repository / entry["path"]).resolve()
            if not path.is_file():
                blockers.append({
                    "id": f"S01-CORPUS-{kind}-missing-{len(evidence)}",
                    "dependency": str(path), "reason": "Declared authentic artifact does not exist.",
                    "attempted_route": "Local file lookup",
                    "next_action": "Provide the original file; do not generate a replacement.",
                })
                continue
            digest = sha256(path.read_bytes()).hexdigest()
            evidence.append({
                "kind": kind, "path": str(path), "sha256": digest,
                "origin": entry["origin"],
                "status": "pending_independent_review",
                "independently_verified": False,
            })
            blockers.append({
                "id": f"S01-CORPUS-{kind}-review-{len(evidence)}",
                "dependency": str(path),
                "reason": "File existence/checksum does not establish authentic origin, applicability or independent expected values.",
                "attempted_route": "Read bytes and calculate checksum only",
                "next_action": "Independently review origin, record locators, dates and source meaning before admission.",
            })
    return evidence, blockers


def prepare_acceptance(config_path: Path, suite: str, fresh: bool, repository: Path) -> Path:
    """Publish a fresh, non-overwriting inventory/blocker report; never return a pass."""
    start = _timestamp()
    run_id = uuid.uuid4().hex
    config_path = config_path.resolve()
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    if not isinstance(config, dict) or config.get("schema_version") != "1":
        raise ValueError("Acceptance configuration needs schema_version: '1'")
    inventory = extract_inventory(repository / config["plan"])
    corpus, blockers = _inspect_corpus(config, repository)
    audit = legacy_audit(repository)
    blockers.extend([
        {
            "id": "S01-ATOMIC-REGISTRY",
            "dependency": "All 297 families and child variables",
            "reason": "Source-specific atomic definitions, units, formulas, applicability, tolerances and independent expectations are not frozen.",
            "attempted_route": "Read all feature, source, instrument and case rows from Plan.md",
            "next_action": "Expand children from actual source documentation and acceptance records; keep all families in the denominator.",
        },
        {
            "id": "S01-SOURCE-BINDINGS",
            "dependency": "SRC-001 through SRC-059, including every product/transport",
            "reason": "Candidate institutions and routes are not verified product-field bindings.",
            "attempted_route": "Preserved all required source categories without substituting another provider's success",
            "next_action": "Identify exact products/fields, units, licences, versions, owning steps and real access/import evidence.",
        },
        {
            "id": "S01-LEGACY-AUDIT",
            "dependency": "Legacy modules, configuration and tests listed in legacy_audit.json",
            "reason": "Legacy implementation has been retired; old user data/cache assets remain ineligible until individually provenance-verified.",
            "attempted_route": "Archived baseline source before removal; only new contract modules are executed",
            "next_action": "Admit only explicitly reviewed authentic assets; do not reuse legacy generated data.",
        },
    ])
    database = config.get("database", {})
    env_name = database.get("connection_environment_variable")
    database_configured = bool(env_name and os.environ.get(env_name))
    blockers.append({
        "id": "S02-DATABASE",
        "dependency": "DB-01 through DB-09",
        "reason": (
            "A connection setting is present. Preparatory storage evidence is separate; the full DB-01..DB-09 contract is not certified."
            if database_configured else
            "No database connection is present in the configured environment variable."
        ),
        "attempted_route": "Environment-variable presence check only; no credentials or connection values exported",
        "next_action": "Complete S01 and all shared/domain DB cases; see linked preparatory evidence without treating it as a gate pass.",
    })
    for step in inventory["steps"]:
        step["status"] = "blocked"
        step["feature_ids"] = [
            feature["id"] for feature in inventory["features"] if step["id"] in feature["owning_steps"]
        ]
        step["source_bindings"] = []
        step["evidence_paths"] = ["requirements_inventory.json", "corpus_audit.json"]
        step["test_results"] = []
        step["blockers"] = (
            [b["id"] for b in blockers if b["id"].startswith("S01")]
            if step["id"] == "S01" else
            [f"{step['prerequisites'][0]} exit gate has not passed"]
        )

    cases = []
    for category in ("sources", "instruments"):
        for requirement in inventory[category]:
            for case_id in requirement["required_cases"]:
                cases.append({
                    "test_case_id": case_id,
                    "requirement_id": requirement["id"],
                    "instance_level": "category_only",
                    "status": "blocked",
                    "executed": False,
                    "reason": "Concrete product/binding/device acceptance contexts and implementation are not available.",
                    "evidence_paths": [],
                })
    for case in inventory["cases"]:
        if case["id"].startswith(("CONN-", "DEVICE-")):
            continue
        cases.append({
            "test_case_id": case["id"], "requirement_id": case["id"],
            "instance_level": "template_only", "status": "blocked", "executed": False,
            "reason": "S01 corpus/atomic registry is incomplete; required test instances cannot be fully discovered.",
            "evidence_paths": [],
        })

    report = {
        "schema_version": "1", "run_id": run_id, "suite": suite,
        "status": "blocked", "overall_complete": False,
        "started_at": start, "finished_at": _timestamp(),
        "fresh_requested": fresh, "fresh_requests_executed": 0,
        "scientific_tests_executed": 0,
        "discovery_complete": False,
        "required_atomic_test_instance_count": None,
        "plan_sha256": inventory["plan_sha256"],
        "config_sha256": sha256(config_bytes).hexdigest(),
        "implementation_files": {
            str(path.relative_to(repository)): sha256(path.read_bytes()).hexdigest()
            for path in sorted((repository / "src" / "agri_data" / "contracts").glob("*.py"))
        },
        "runtime_dependencies": {name: version(name) for name in ("pydantic", "PyYAML")},
        "preparatory_storage_evidence": config.get("preparatory_storage_evidence"),
        "counts": inventory["counts"],
        "completed_steps": 0, "completed_features": 0,
        "blockers": blockers, "case_status": cases,
        "limitations": [
            "This report inventories requirements; it is not a passed connection, database, domain or end-to-end test.",
            "Unexpanded variables/products/contexts make the full required test denominator unknown, never zero.",
            "No provider request, agricultural data generation, legacy test or SQLite connection was performed.",
        ],
    }
    output = repository / config["output_root"] / run_id
    output.mkdir(parents=True, exist_ok=False)
    outputs = {
        "requirements_inventory.json": inventory,
        "observation.schema.json": Observation.model_json_schema(),
        "corpus_audit.json": corpus,
        "legacy_audit.json": audit,
        "implementation_ledger.json": {"schema_version": "1", "overall_complete": False, "steps": inventory["steps"]},
        "validation_report.json": report,
    }
    for filename, payload in outputs.items():
        _write_json(output / filename, payload)
    rows = [
        "# Acceptance blocked",
        "",
        "S01 is incomplete. No acquisition/database/scientific acceptance gates have passed.",
        "",
        f"Inventory: {inventory['counts']['features']} families, {inventory['counts']['sources']} source categories, "
        f"{inventory['counts']['instruments']} instrument categories.",
        "",
        "Atomic-variable and product/context expansion remains blocked; coverage cannot be reported as complete.",
        "",
    ]
    rows.extend(f"- **{b['id']}**: {b['reason']} Next action: {b['next_action']}" for b in blockers)
    (output / "validation_report.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": "1", "bundle_kind": "s01_contract_preparation",
        "run_id": run_id, "status": "blocked", "started_at": start, "finished_at": _timestamp(),
        "plan_sha256": inventory["plan_sha256"], "config_sha256": sha256(config_bytes).hexdigest(),
        "files": [
            {"path": path.name, "sha256": sha256(path.read_bytes()).hexdigest(), "byte_count": path.stat().st_size}
            for path in sorted(output.iterdir()) if path.is_file()
        ],
    }
    temporary = output / "manifest.json.pending"
    _write_json(temporary, manifest)
    temporary.replace(output / "manifest.json")
    return output
