from pathlib import Path
import runpy
import socket

import pytest


require_free_ports = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts" / "browser_acceptance.py")
)["require_free_ports"]


def test_browser_harness_refuses_an_existing_service():
    with socket.socket() as service:
        service.bind(("127.0.0.1", 0))
        service.listen()
        port = service.getsockname()[1]
        with pytest.raises(RuntimeError, match="leave existing services untouched"):
            require_free_ports((port,))
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            connection, _ = service.accept()
            connection.close()


def test_browser_harness_releases_its_probes():
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    require_free_ports((port,))
    with socket.socket() as service:
        service.bind(("127.0.0.1", port))
