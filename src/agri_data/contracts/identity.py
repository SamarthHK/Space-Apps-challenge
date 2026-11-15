"""Shared field identity; provider aliases are reviewed separately from geometry."""

from hashlib import sha256
import json


def stable_field_id(project: str, namespace: str, identifier: str) -> str:
    if not all(value.strip() for value in (project, namespace, identifier)):
        raise ValueError("Field identity requires project, source namespace and provider identifier")
    identity = json.dumps([project, namespace, identifier], separators=(",", ":"))
    return "field_" + sha256(identity.encode()).hexdigest()


def fingerprint(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
