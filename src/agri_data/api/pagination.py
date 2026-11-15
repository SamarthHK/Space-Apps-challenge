"""Opaque cursors tied to a complete read snapshot and its request context."""

import base64
from hashlib import sha256
import hmac
import json
import secrets


class InvalidCursor(Exception):
    pass


class ChangedSnapshot(Exception):
    pass


class Pagination:
    def __init__(self):
        self.key = secrets.token_bytes(32)

    def page(self, rows, context, limit, cursor=None):
        snapshot = sha256(json.dumps([context, rows], sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()
        offset = 0
        if cursor:
            try:
                payload, signature = cursor.split(".")
                if not hmac.compare_digest(hmac.digest(self.key, payload.encode(), "sha256").hex(), signature):
                    raise InvalidCursor()
                decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
                if decoded["context"] != context or type(decoded["offset"]) is not int or decoded["offset"] < 1:
                    raise InvalidCursor()
                if decoded["snapshot"] != snapshot:
                    raise ChangedSnapshot()
                offset = decoded["offset"]
                if offset >= len(rows):
                    raise InvalidCursor()
            except (ValueError, KeyError, TypeError):
                raise InvalidCursor() from None
        data = rows[offset:offset + limit]
        next_cursor = None
        if offset + limit < len(rows):
            payload = base64.urlsafe_b64encode(json.dumps(
                {"context": context, "snapshot": snapshot, "offset": offset + limit},
                separators=(",", ":"),
            ).encode()).decode().rstrip("=")
            next_cursor = payload + "." + hmac.digest(self.key, payload.encode(), "sha256").hex()
        return data, next_cursor
