"""Explicit India acquisition/model commands; unavailable evidence never becomes a fallback."""

import json
from pathlib import Path
import sys

import yaml


COMMANDS = {"acquire-crop-profiles", "build-crop-profiles", "acquire-india-outcomes", "build-india-outcomes",
            "acquire-gaez-reference", "build-gaez-reference", "build-india-registry",
            "acquire-india-environment", "build-india-environment", "build-india-dataset"}


def register_commands(commands):
    acquire = commands.add_parser("acquire-crop-profiles", help="Acquire authentic EcoCrop requirement profiles")
    acquire.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    acquire.add_argument("--output", type=Path, required=True)
    build = commands.add_parser("build-crop-profiles", help="Normalize, persist and export versioned crop requirements")
    build.add_argument("--corpus", type=Path, required=True)
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    acquire_outcomes = commands.add_parser("acquire-india-outcomes", help="Acquire official Indian district APY reports")
    acquire_outcomes.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    acquire_outcomes.add_argument("--output", type=Path, required=True)
    build_outcomes = commands.add_parser("build-india-outcomes", help="Persist real Indian statistical outcomes and source units")
    build_outcomes.add_argument("--corpus", type=Path, required=True)
    build_outcomes.add_argument("--config", type=Path, required=True)
    build_outcomes.add_argument("--output", type=Path, required=True)
    acquire_reference = commands.add_parser("acquire-gaez-reference", help="Acquire real, comparable GAEZ reference products")
    acquire_reference.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    acquire_reference.add_argument("--output", type=Path, required=True)
    acquire_reference.add_argument("--resume", action="store_true")
    build_reference = commands.add_parser("build-gaez-reference", help="Normalize matched native-grid Indian reference evidence")
    build_reference.add_argument("--corpus", type=Path, required=True)
    build_reference.add_argument("--config", type=Path, required=True)
    build_reference.add_argument("--output", type=Path, required=True)
    registry = commands.add_parser("build-india-registry", help="Link source-qualified crop identities without relabelling outcomes")
    registry.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    registry.add_argument("--profiles", type=Path, required=True)
    registry.add_argument("--outcomes", type=Path, required=True)
    registry.add_argument("--gaez-corpus", type=Path, required=True)
    registry.add_argument("--config", type=Path, required=True)
    registry.add_argument("--output", type=Path, required=True)
    environment = commands.add_parser("acquire-india-environment", help="Acquire exact-period NASA monthly reference histories")
    environment.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    environment.add_argument("--gaez-corpus", type=Path, required=True)
    environment.add_argument("--output", type=Path, required=True)
    environment.add_argument("--resume", action="store_true")
    build_environment = commands.add_parser("build-india-environment", help="Persist complete-period NASA normals on native grids")
    build_environment.add_argument("--corpus", type=Path, required=True)
    build_environment.add_argument("--config", type=Path, required=True)
    build_environment.add_argument("--output", type=Path, required=True)
    dataset = commands.add_parser("build-india-dataset", help="Freeze source-linked reference features and crop-covered spatial splits")
    dataset.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    for argument in ("gaez", "nasa", "registry", "profiles", "config", "output"):
        dataset.add_argument("--" + argument, type=Path, required=True)


def database_store(config_path):
    from .postgres import PostgresStore
    config = yaml.safe_load(Path(config_path).read_bytes())["database"]
    return PostgresStore(config["expected_database"], config["expected_user"],
                         config["acceptance_schema"], config["connection_environment_variable"])


def run(args):
    try:
        from .crop_requirements import acquire_crop_profiles, build_crop_profiles
        if args.command == "acquire-crop-profiles":
            result = {"corpus": str(acquire_crop_profiles(args.contract, args.output).resolve())}
        elif args.command == "build-crop-profiles":
            result = build_crop_profiles(args.corpus, args.output, database_store(args.config))
        elif args.command == "acquire-india-outcomes":
            from .india_outcomes import acquire_india_outcomes
            result = {"corpus": str(acquire_india_outcomes(args.contract, args.output).resolve())}
        elif args.command == "build-india-outcomes":
            from .india_outcomes import build_india_outcomes
            result = build_india_outcomes(args.corpus, args.output, database_store(args.config))
        elif args.command == "acquire-gaez-reference":
            from .gaez import acquire_gaez
            result = {"corpus": str(acquire_gaez(args.contract, args.output, args.resume).resolve())}
        elif args.command == "build-gaez-reference":
            from .gaez import build_gaez
            result = build_gaez(args.corpus, args.output, database_store(args.config))
        elif args.command == "build-india-registry":
            from .india_registry import build_india_registry
            result = build_india_registry(args.contract, args.profiles, args.outcomes, args.gaez_corpus,
                                          args.output, database_store(args.config))
        elif args.command == "acquire-india-environment":
            from .india_environment import acquire_india_environment
            result = {"corpus": str(acquire_india_environment(args.contract, args.gaez_corpus, args.output, args.resume).resolve())}
        elif args.command == "build-india-environment":
            from .india_environment import build_india_environment
            result = build_india_environment(args.corpus, args.output, database_store(args.config))
        elif args.command == "build-india-dataset":
            from .india_dataset import build_reference_dataset
            result = build_reference_dataset(args.contract, args.gaez, args.nasa, args.registry,
                                             args.profiles, args.output, database_store(args.config))
        else:
            raise ValueError("Unsupported India command")
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(f"India pipeline failed ({type(error).__name__}); inspect the input contract and failure receipts.",
              file=sys.stderr)
        return 2
