"""Run with python -m agri_data.api; no import-time connection or migration."""

import argparse
import json
from pathlib import Path

import uvicorn

from .app import create_app
from .config import Settings
from .data import DataSettings
from agri_data.workspace.settings import WorkspaceSettings


def main():
    parser = argparse.ArgumentParser(description="Trusted-network workspace API with shared or private-account access")
    parser.add_argument("--export-openapi", type=Path)
    args = parser.parse_args()
    settings = Settings.from_env()
    app = create_app(settings, DataSettings.from_env(), WorkspaceSettings.from_env())
    if args.export_openapi:
        args.export_openapi.write_bytes(
            (json.dumps(app.openapi(), indent=2, ensure_ascii=True) + "\n").encode("utf-8"),
        )
    else:
        uvicorn.run(app, host=settings.bind_host, port=settings.port, proxy_headers=False)


if __name__ == "__main__":
    main()
