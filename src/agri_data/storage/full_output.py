"""Lossless observation bundles and reproducible, non-destructive filtered views."""
import hashlib
import json
from pathlib import Path
from datetime import date, datetime


def encode(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def write_bundle(rows, directory, metadata=None):
    """Write every input record, including unknown columns, without rounding or limits."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / "observations.jsonl"
    count = 0
    with target.open("w", encoding="utf-8") as output:
        for row in rows:
            output.write(json.dumps(row, default=encode, allow_nan=False) + "\n")
            count += 1
    manifest = {"schema_version": 1, "row_count": count,
                "file": target.name, "sha256": checksum(target), "metadata": metadata or {}}
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2, default=encode), encoding="utf-8")
    return manifest


def filter_bundle(source, destination, filters):
    """Filter a complete JSONL artifact into a new directory; never edit the input."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if destination == source.parent or source.is_relative_to(destination):
        raise ValueError("Filtered output must be separate from the source bundle")
    allowed = {"field_id", "domain", "variable_id", "source_id", "measurement_type", "quality_flag"}
    if set(filters) - allowed:
        raise ValueError(f"Unsupported filters: {sorted(set(filters) - allowed)}")
    if any(not isinstance(values, list) for values in filters.values()):
        raise ValueError("Each filter must be a list of permitted values")
    before = checksum(source)
    counts = {"input": 0, "selected": 0}

    def selected():
        with source.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                counts["input"] += 1
                if all(row.get(key) in values for key, values in filters.items()):
                    counts["selected"] += 1
                    yield row

    manifest = write_bundle(selected(), destination, {"source": str(source), "source_sha256": before, "filters": filters})
    if checksum(source) != before:
        raise RuntimeError("Input changed during filtering; output cannot be certified")
    manifest["counts"] = counts
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
