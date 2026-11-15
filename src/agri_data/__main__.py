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
    health = commands.add_parser("health-check", help="Run live engineering checks without requiring scientific approval")
    health.add_argument("--config", type=Path, required=True)
    health.add_argument("--output", type=Path, required=True)
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
    reconcile = commands.add_parser("reconcile-data", help="Resolve reviewed field aliases and scientific duplicates")
    reconcile.add_argument("--config", type=Path, required=True)
    reconcile.add_argument("--corpus", type=Path)
    trials = commands.add_parser("acquire-trials", help="Acquire the published CC-BY Woburn empirical trial")
    trials.add_argument("--output", type=Path, required=True)
    trial_import = commands.add_parser("import-trials", help="Import Woburn outcome evidence, retaining pending status")
    trial_import.add_argument("--config", type=Path, required=True)
    trial_import.add_argument("--manifest", type=Path, required=True)
    snapshot = commands.add_parser("prepare-ml", help="Export an immutable dataset snapshot and training blockers")
    snapshot.add_argument("--config", type=Path, required=True)
    snapshot.add_argument("--contract", type=Path, default=Path("config") / "ml_dataset.yaml")
    snapshot.add_argument("--output", type=Path, required=True)
    acquire_outcomes = commands.add_parser("acquire-outcomes", help="Acquire published multicrop trials and site-matched NASA history")
    acquire_outcomes.add_argument("--contract", type=Path, default=Path("config") / "outcome_model.yaml")
    acquire_outcomes.add_argument("--output", type=Path, required=True)
    build_outcomes = commands.add_parser("build-outcomes", help="Persist and export authentic multicrop modeling records")
    build_outcomes.add_argument("--config", type=Path, required=True)
    build_outcomes.add_argument("--corpus", type=Path, required=True)
    build_outcomes.add_argument("--output", type=Path, required=True)
    train_outcomes = commands.add_parser("train-outcomes", help="Train and evaluate retrospective crop outcome models")
    train_outcomes.add_argument("--dataset", type=Path, required=True)
    train_outcomes.add_argument("--output", type=Path, required=True)
    predict_outcome = commands.add_parser("predict-outcome", help="Research prediction from a complete prepared feature record")
    predict_outcome.add_argument("--model", type=Path, required=True)
    predict_outcome.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    repository = Path.cwd()
    if args.command in ("acquire-outcomes", "build-outcomes", "train-outcomes", "predict-outcome"):
        import json
        import yaml
        from agri_data.contracts.outcome_data import acquire_outcome_corpus, build_outcome_dataset
        try:
            if args.command == "acquire-outcomes":
                result = {"corpus": str(acquire_outcome_corpus(args.contract, args.output).resolve())}
            elif args.command == "train-outcomes":
                from agri_data.contracts.outcome_model import train_outcomes
                result = train_outcomes(args.dataset, args.output)
            elif args.command == "predict-outcome":
                from agri_data.contracts.outcome_model import predict_example
                result = predict_example(args.model, json.loads(args.input.read_bytes()))
            else:
                from agri_data.contracts.postgres import PostgresStore
                database = yaml.safe_load(args.config.read_bytes())["database"]
                store = PostgresStore(database["expected_database"], database["expected_user"],
                                      database["acceptance_schema"], database["connection_environment_variable"])
                result = build_outcome_dataset(args.corpus, args.output, store)
            print(json.dumps(result, indent=2))
            return 0
        except Exception as error:
            print(f"Outcome pipeline failed ({type(error).__name__}): inspect the input contract and failure receipts.",
                  file=sys.stderr)
            return 2
    if args.command == "health-check":
        import json
        from agri_data.contracts.health import run_health
        try:
            result = run_health(args.config, args.output, repository)
        except (OSError, ValueError, KeyError) as exc:
            print(f"Health-check setup failed ({type(exc).__name__}); check configuration and output paths.",
                  file=sys.stderr)
            return 2
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "passed" else 2
    if args.command == "acquire-reference":
        from agri_data.contracts.corpus import acquire_reference_corpus
        print(acquire_reference_corpus(args.output)["manifest"])
        return 0
    if args.command == "acquire-trials":
        from agri_data.contracts.trials import acquire_woburn
        print(acquire_woburn(args.output))
        return 0
    if args.command in ("storage-proof", "ingest-boundaries", "reconcile-data", "import-trials", "prepare-ml"):
        import json
        import yaml
        from agri_data.contracts.postgres import PostgresStore
        from agri_data.contracts.storage_proof import run_storage_proof
        config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
        database = config["database"]
        store = PostgresStore(database["expected_database"], database["expected_user"],
                              database["acceptance_schema"], database["connection_environment_variable"])
        if args.command == "reconcile-data":
            from agri_data.contracts.canonical import reconcile_reference
            print(json.dumps(reconcile_reference(store, args.corpus or repository / config["reference_corpus_manifest"]), indent=2))
            return 0
        if args.command == "import-trials":
            from agri_data.contracts.trials import import_woburn
            print(json.dumps(import_woburn(store, args.manifest), indent=2))
            return 0
        if args.command == "prepare-ml":
            from agri_data.contracts.ml_dataset import export_preparation
            print(json.dumps(export_preparation(store, args.contract, args.output, repository), indent=2))
            return 2
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
