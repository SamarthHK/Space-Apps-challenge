"""Explicit India acquisition/model commands; unavailable evidence never becomes a fallback."""

import json
from pathlib import Path
import sys

import yaml


COMMANDS = {"acquire-crop-profiles", "build-crop-profiles"}


def register_commands(commands):
    acquire = commands.add_parser("acquire-crop-profiles", help="Acquire authentic EcoCrop requirement profiles")
    acquire.add_argument("--contract", type=Path, default=Path("config") / "india_model.yaml")
    acquire.add_argument("--output", type=Path, required=True)
    build = commands.add_parser("build-crop-profiles", help="Normalize, persist and export versioned crop requirements")
    build.add_argument("--corpus", type=Path, required=True)
    build.add_argument("--config", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)


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
        else:
            raise ValueError("Unsupported India command")
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except Exception as error:
        print(f"India pipeline failed ({type(error).__name__}); inspect the input contract and failure receipts.",
              file=sys.stderr)
        return 2
