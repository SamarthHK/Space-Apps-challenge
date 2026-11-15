"""Explicit administrative commands; never provision an account on startup."""

import argparse
import getpass
import json
from pathlib import Path

from agri_data.services.database import migrate, verify_schema
from agri_data.services.identity import create_account, revoke_user_sessions
from .settings import ApiSettings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate")
    account = commands.add_parser("create-user")
    account.add_argument("login")
    revoke = commands.add_parser("revoke-sessions")
    revoke.add_argument("login")
    contract = commands.add_parser("openapi")
    contract.add_argument("output", type=Path)
    args = parser.parse_args()
    settings = ApiSettings()
    if args.command == "migrate":
        migrate(settings)
        verify_schema(settings)
        print("Schema verified.")
    elif args.command == "create-user":
        verify_schema(settings)
        password = getpass.getpass("Password (at least 12 characters): ")
        if password != getpass.getpass("Confirm password: "):
            parser.error("Passwords do not match")
        print(f"User created: {create_account(settings, args.login, password)}")
    elif args.command == "revoke-sessions":
        print(f"Revoked sessions: {revoke_user_sessions(settings, args.login)}")
    else:
        from .app import create_app

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(create_app(settings).openapi(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
