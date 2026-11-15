import argparse

from .errors import WorkspaceUnavailable
from .settings import WorkspaceSettings
from .store import WorkspaceStore


def main():
    parser = argparse.ArgumentParser(description="Explicit shared-workspace setup; no accounts")
    parser.add_argument("command", choices=["provision", "check"])
    args = parser.parse_args()
    try:
        store = WorkspaceStore(WorkspaceSettings.from_env())
        if args.command == "provision":
            store.provision()
        if not store.ready():
            raise WorkspaceUnavailable("Workspace is not ready; check configuration and provisioning")
    except (ValueError, WorkspaceUnavailable) as error:
        parser.exit(2, f"{error}\n")
    print("Shared workspace storage is ready.")


if __name__ == "__main__":
    main()
