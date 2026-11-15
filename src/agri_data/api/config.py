"""Fail-closed configuration for loopback or Tailscale-only serving."""

from dataclasses import dataclass, field
from ipaddress import ip_address, ip_network
import os
import re
from pathlib import Path
from urllib.parse import urlsplit


TAILNET = ip_network("100.64.0.0/10")


def private_host(host):
    if host == "localhost":
        return True
    try:
        address = ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address in TAILNET


def origin(value):
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError("Invalid frontend origin") from None
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or not private_host(parsed.hostname)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
        or port == 0
    ):
        raise ValueError("Frontend origins must be explicit loopback or Tailscale HTTP(S) origins")
    return value.rstrip("/")


@dataclass(frozen=True)
class Settings:
    bind_host: str
    port: int
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        host = environ.get("AGRI_API_HOST", "127.0.0.1")
        if not private_host(host):
            raise ValueError("Bind to loopback or a Tailscale IP, never a wildcard/public address")
        try:
            port = int(environ.get("AGRI_API_PORT", "8000"))
        except ValueError:
            raise ValueError("AGRI_API_PORT must be an integer from 1 to 65535") from None
        if not 1 <= port <= 65535:
            raise ValueError("AGRI_API_PORT must be an integer from 1 to 65535")
        supplied = environ.get("AGRI_ALLOWED_ORIGINS", "")
        if not supplied.strip():
            raise ValueError("AGRI_ALLOWED_ORIGINS must explicitly list frontend origins")
        origins = tuple(dict.fromkeys(origin(item.strip()) for item in supplied.split(",")))
        return cls(host, port, origins)

    @property
    def allowed_hosts(self):
        return tuple(dict.fromkeys([self.bind_host, *(urlsplit(item).hostname for item in self.allowed_origins)]))


def request_id(value):
    return value if value and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) else None


@dataclass(frozen=True)
class ReferenceSettings:
    model_dir: Path = field(repr=False)
    model_id: str

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        directory = environ.get("AGRI_REFERENCE_MODEL_DIR", "").strip()
        identifier = environ.get("AGRI_REFERENCE_MODEL_ID", "").strip()
        if not directory and not identifier:
            return None
        if not directory or not re.fullmatch(r"[0-9a-f]{64}", identifier):
            raise ValueError("Configure both AGRI_REFERENCE_MODEL_DIR and a 64-character AGRI_REFERENCE_MODEL_ID")
        if "://" in directory:
            raise ValueError("The reference model must be an operator-configured local directory")
        return cls(Path(directory).expanduser().resolve(), identifier)
