"""Immutable authentic response storage, with separate request evidence."""

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import uuid
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


def _public_receipt_url(url):
    parts = urlsplit(url)
    keys = {"token", "access_token", "api_key", "key", "sig", "signature", "client_secret"}
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key.casefold() not in keys and not key.casefold().startswith(("x-amz-", "x-goog-"))]
    return urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, urlencode(query), ""))


def system_trust_session():
    """Use the operating system's certificate verification without disabling TLS."""
    import ssl
    import truststore
    from requests.adapters import HTTPAdapter

    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    class SystemTrustAdapter(HTTPAdapter):
        def build_connection_pool_key_attributes(self, request, verify, cert=None):
            if verify is not True:
                raise ValueError("System-trust acquisition requires certificate verification")
            host, options = super().build_connection_pool_key_attributes(request, verify, cert)
            options["ssl_context"] = context
            return host, options

    session = requests.Session()
    session.mount("https://", SystemTrustAdapter())
    return session


def archive_response(url: str, destination: Path, params=None, timeout=60, *,
                     session=None, method="GET", data=None) -> dict:
    """Make a fresh public request; never use a cache to establish connectivity."""
    if method not in ("GET", "POST") or (method == "GET" and data is not None):
        raise ValueError("Acquisition supports GET or a public POST form")
    started = datetime.now(timezone.utc).isoformat()
    destination.mkdir(parents=True, exist_ok=True)
    try:
        response = (session or requests).request(method, url, params=params, data=data, timeout=timeout)
    except requests.RequestException as error:
        # This path is for public sources. Do not persist arbitrary exception
        # text, which may include authentication or proxy configuration.
        failure = {
            "request_id": uuid.uuid4().hex, "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed", "error_type": type(error).__name__, "fresh": True,
        }
        (destination / (failure["request_id"] + ".failure.json")).write_text(
            json.dumps(failure, indent=2), encoding="utf-8")
        raise
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
        "request_method": method,
        "requested_url": _public_receipt_url((response.history[0] if response.history else response).request.url),
        "response_url": _public_receipt_url(response.url),
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
