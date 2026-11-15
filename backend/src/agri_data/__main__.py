"""Plan-authoritative CLI. Legacy demo/acquisition paths are not executable here."""

import argparse
from pathlib import Path
import sys

from agri_data.contracts.acceptance import prepare_acceptance


def main():
    parser = argparse.ArgumentParser(description="Plan.md agricultural data acceptance gates")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Report required acceptance gates; incomplete gates return nonzero")
    validate.add_argument("--suite", choices=["connections", "database", "features", "all"], required=True)
    validate.add_argument("--config", type=Path, required=True)
    validate.add_argument("--fresh", action="store_true")
    acquire = commands.add_parser("acquire-reference", help="Acquire public authentic infrastructure reference evidence")
    acquire.add_argument("--output", type=Path, required=True)
    proof = commands.add_parser("storage-proof", help="Run preparatory real PostgreSQL readback checks, not full acceptance")
    proof.add_argument("--config", type=Path, required=True)
    proof.add_argument("--corpus", type=Path, help="Override the configured authentic corpus manifest")
    proof.add_argument("--output", type=Path, required=True)
    ingest = commands.add_parser("ingest-boundaries", help="Persist authentic KML/KMZ boundaries and geometric evidence")
    ingest.add_argument("input", type=Path)
    ingest.add_argument("--config", type=Path, required=True)
    ingest.add_argument("--project", required=True)
    ingest.add_argument("--source-namespace", required=True)
    ingest.add_argument("--origin", required=True)
    ingest.add_argument("--output", type=Path, required=True)
    ingest.add_argument("--allow-repair", action="store_true", help="Explicitly allow topology repair while retaining originals")
    ingest.add_argument("--repair-reference", type=Path)
    ingest.add_argument("--repair-area-tolerance-m2", type=float)
    ingest.add_argument("--repair-shape-tolerance-m2", type=float)
    args = parser.parse_args()
    repository = Path.cwd()
    if args.command == "acquire-reference":
        from agri_data.contracts.corpus import acquire_reference_corpus
        print(acquire_reference_corpus(args.output)["manifest"])
        return 0
    if args.command in ("storage-proof", "ingest-boundaries"):
        import json
        import yaml
        from agri_data.contracts.postgres import PostgresStore
        from agri_data.contracts.storage_proof import run_storage_proof
        config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
        database = config["database"]
        store = PostgresStore(database["expected_database"], database["expected_user"],
                              database["acceptance_schema"], database["connection_environment_variable"])
        if args.command == "ingest-boundaries":
            from agri_data.contracts.boundary_import import ingest_boundaries
            result = ingest_boundaries(
                args.input, args.project, args.source_namespace, args.origin, store,
                args.output, repository / "data" / "raw" / "boundary-imports",
                allow_repair=args.allow_repair,
                repair_reference=args.repair_reference,
                repair_area_tolerance_m2=args.repair_area_tolerance_m2,
                repair_shape_tolerance_m2=args.repair_shape_tolerance_m2,
            )
            print(json.dumps(result, indent=2))
            return 0 if result["status"] == "complete" else 2
        corpus = args.corpus or repository / config["reference_corpus_manifest"]
        result = run_storage_proof(corpus, store, args.output, repository)
        print(json.dumps(result, indent=2))
        return 0
    try:
        output = prepare_acceptance(args.config, args.suite, args.fresh, repository)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Acceptance configuration/inventory failed: {exc}", file=sys.stderr)
        return 2
    print(f"BLOCKED: S01 prerequisites and registry expansion are incomplete. Report: {output}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
