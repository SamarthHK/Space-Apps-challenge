"""Extract the complete requirement denominator from the authoritative plan.

Inventory entries describe requirements, not acquired agricultural observations.
Product-specific atomic definitions require independently verified source documents.
"""

from collections import Counter
from hashlib import sha256
from pathlib import Path
import re
import zipfile


FEATURE = re.compile(r"F\d{2}-\d{3}")
SOURCE = re.compile(r"SRC-\d{3}")
DEVICE = re.compile(r"INST-\d{2}")
CASE = re.compile(r"(?:DB|CONN|FEAT|GEO|CROSS|DEVICE|E2E)-\d{2}|Q\d{2}")
STEP = re.compile(r"S\d{2}")
EXPECTED_COUNTS = {"features": 297, "sources": 59, "instruments": 14, "steps": 11, "cases": 68}

SUPPLEMENTARY_OWNERS = {
    "F16-001": ["S03"],
    "F16-002": ["S03"],
    "F16-003": ["S03", "S05", "S06"],
    "F16-004": ["S03", "S05", "S06"],
    "F16-005": ["S08"],
    "F16-006": ["S07"],
    "F16-007": ["S07"],
    "F16-008": ["S07"],
    "F16-009": ["S08"],
    "F16-010": ["S08"],
    "F16-011": ["S07"],
    "F16-012": ["S09"],
    "F16-013": ["S09"],
    "F16-014": ["S07", "S09"],
    "F16-015": ["S07", "S09"],
    "F16-016": ["S05", "S06", "S07", "S08", "S09"],
    "F16-017": ["S07"],
    "F16-018": ["S05", "S06"],
    "F16-019": ["S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10"],
    "F16-020": ["S08"],
}


def extract_inventory(plan_path: Path) -> dict:
    """Preserve every table requirement verbatim and fail on inventory drift."""
    payload = plan_path.read_bytes()
    inventory = {key: [] for key in EXPECTED_COUNTS}
    for line_number, line in enumerate(payload.decode("utf-8").splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        first = cells[0]
        identifier = first.split()[0] if first else ""
        entry = {"id": identifier, "plan_line": line_number, "columns": cells, "status": "not_started"}
        if FEATURE.fullmatch(first):
            family = int(first[1:3])
            if family == 16:
                owners = SUPPLEMENTARY_OWNERS[first]
            else:
                owners = ["S05" if family <= 4 else "S06" if family <= 8 else "S07" if family <= 12 else "S08"]
            entry.update(
                name=cells[1],
                required_content=cells[2],
                candidate_sources=cells[3] if len(cells) > 3 else None,
                owning_steps=owners,
                quality_profile=f"Q{family:02d}",
                required_feature_cases=[f"FEAT-{i:02d}" for i in range(1, 10)],
                atomic_variables=[],
                expansion_status="blocked",
                blocker="Source-specific child definitions, dimensions, units, bindings and independent expectations are not verified.",
            )
            inventory["features"].append(entry)
        elif SOURCE.fullmatch(first):
            entry.update(
                name=cells[1], required_data=cells[2], planned_route=cells[3],
                access_constraint=cells[4], products=[], source_bindings=[],
                required_cases=[f"CONN-{i:02d}" for i in range(1, 9)],
                blocker="Concrete product/import artifact, licence, metadata and positive evidence have not been verified.",
            )
            inventory["sources"].append(entry)
        elif DEVICE.fullmatch(first):
            entry.update(
                name=cells[1], required_data=cells[2], scientific_checks=cells[3],
                instances=[], owning_steps=["S09"],
                required_cases=[f"DEVICE-{i:02d}" for i in range(1, 7)],
                blocker="Authentic device/report, installation/sample and calibration evidence not supplied.",
            )
            inventory["instruments"].append(entry)
        elif CASE.fullmatch(identifier):
            inventory["cases"].append(entry)
        elif STEP.fullmatch(identifier):
            entry.update(prerequisites=[] if identifier == "S01" else [f"S{int(identifier[1:]) - 1:02d}"])
            inventory["steps"].append(entry)

    for kind, expected in EXPECTED_COUNTS.items():
        entries = inventory[kind]
        duplicates = [key for key, count in Counter(e["id"] for e in entries).items() if count > 1]
        if len(entries) != expected or duplicates:
            raise ValueError(
                f"Plan inventory mismatch for {kind}: expected {expected}, found {len(entries)}, duplicates={duplicates}. "
                "Review the plan revision before changing the coverage denominator."
            )
    return {
        "schema_version": "1",
        "plan_path": str(plan_path.resolve()),
        "plan_sha256": sha256(payload).hexdigest(),
        "registry_status": "in_progress",
        "atomic_denominator_frozen": False,
        "verified_atomic_variables": [],
        "counts": {kind: len(entries) for kind, entries in inventory.items()},
        **inventory,
    }


def legacy_audit(repository: Path) -> list[dict]:
    """Identify legacy entry points/assets that are ineligible until provenance review."""
    groups = {
        "generated_boundary": ["data/input/farm_area.kml"],
        "unverified_crop_constants": ["config/crop_catalog.yaml"],
        "generated_or_unverified_scientific_values": [
            "src/agri_data/sources/nasa_power.py",
            "src/agri_data/sources/soilgrids.py",
            "src/agri_data/sources/gee.py",
            "src/agri_data/sources/cgwb.py",
            "src/agri_data/sources/faostat.py",
            "src/agri_data/sources/soil_health_card.py",
            "src/agri_data/crop/development.py",
            "src/agri_data/processing/terrain.py",
            "src/agri_data/processing/soil.py",
            "src/agri_data/rotation/compatibility.py",
            "src/agri_data/rotation/residue.py",
        ],
        "legacy_tests_not_acceptance_evidence": [
            "tests/test_acquisition_modes.py",
            "tests/test_sources_and_database.py",
            "tests/test_geo_and_processing.py",
            "tests/test_orchestration_import.py",
            "tests/test_rotation.py",
            "tests/test_imports.py",
            "tests/test_full_output.py",
        ],
        "sqlite_storage_not_acceptable": ["src/agri_data/storage/database.py"],
    }
    entries = []
    archive_path = repository / ".local" / "legacy-backend-5af5373.zip"
    archive = zipfile.ZipFile(archive_path) if archive_path.exists() else None
    for reason, paths in groups.items():
        for relative in paths:
            path = repository.joinpath(*relative.split("/"))
            payload = path.read_bytes() if path.is_file() else (
                archive.read(relative) if archive and relative in archive.namelist() else None
            )
            if payload is not None:
                entries.append({
                    "path": str(path.relative_to(repository)),
                    "sha256": sha256(payload).hexdigest(),
                    "reason": reason,
                    "eligible_for_acceptance": False,
                    "disposition": "Ineligible data preserved" if path.is_file() else "Retired source; preserved in Git and local archive",
                })
    if archive:
        archive.close()
    return entries
