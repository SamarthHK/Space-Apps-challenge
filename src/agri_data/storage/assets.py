"""
Source asset tracking and provenance module.
Computes cryptographic SHA-256 checksums, registers raw files, and ensures raw immutability.
"""

from pathlib import Path
from typing import Optional, Dict, Any
import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from .models import SourceAsset


def calculate_sha256(file_path: Path) -> str:
    """Calculates SHA-256 hash of a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def register_source_asset(
    session: Session,
    file_path: Path,
    file_format: str,
    dataset_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> SourceAsset:
    """
    Registers a raw or processed asset into source_assets table.
    If the file with identical checksum already exists, returns the existing record.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    checksum = calculate_sha256(path)
    file_size = path.stat().st_size

    existing = session.query(SourceAsset).filter_by(sha256_checksum=checksum).first()
    if existing:
        return existing

    asset = SourceAsset(
        dataset_id=dataset_id,
        file_path=str(path.resolve()),
        file_format=file_format.lower(),
        sha256_checksum=checksum,
        byte_size=file_size,
        retrieved_at=datetime.utcnow(),
        metadata_json=metadata or {}
    )
    session.add(asset)
    session.flush()
    return asset
