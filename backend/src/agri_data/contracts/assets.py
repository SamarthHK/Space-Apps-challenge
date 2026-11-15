"""Immutable authentic response storage, with separate request evidence."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import uuid

import requests


def archive_response(url: str, destination: Path, params=None, timeout=60) -> dict:
    """Make a fresh public request; never use a cache to establish connectivity."""
    started = datetime.now(timezone.utc).isoformat()
    response = requests.get(url, params=params, timeout=timeout)
    payload = response.content
    digest = sha256(payload).hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    asset = destination / digest
    try:
        with asset.open("xb") as stream:
            stream.write(payload)
    except FileExistsError:
        if sha256(asset.read_bytes()).hexdigest() != digest:
            raise ValueError("Previously archived raw bytes have changed")
    evidence = {
        "request_id": uuid.uuid4().hex,
        "requested_url": response.request.url,
        "response_url": response.url,
        "http_status": response.status_code,
        "content_type": response.headers.get("Content-Type"),
        "etag": response.headers.get("ETag"),
        "last_modified": response.headers.get("Last-Modified"),
        "started_at": started,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "raw_path": str(asset.resolve()),
        "raw_sha256": digest,
        "byte_count": len(payload),
        "fresh": True,
    }
    with (destination / f"{evidence['request_id']}.request.json").open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2)
    response.raise_for_status()
    return evidence
