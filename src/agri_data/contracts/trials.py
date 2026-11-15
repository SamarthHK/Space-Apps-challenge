"""Version-specific importer for a genuine published rotation experiment.

No preceding crop is inferred from an ambiguous treatment code. Original factor
tables, notes and missing outcomes remain available; records are not ML-approved.
"""

import csv
from collections import Counter
from datetime import date
from decimal import Decimal
from hashlib import md5, sha256
from io import BytesIO, StringIO
import json
from pathlib import Path
import zipfile

from defusedxml import ElementTree as ET
from psycopg.types.json import Jsonb

from .assets import archive_response
from .identity import fingerprint


DOI = "10.23637/wrn3-wheat7618-01"
LANDING = "https://www.era.rothamsted.ac.uk/dataset/wrn3/01-WH7618"
DOWNLOAD = "https://www.era.rothamsted.ac.uk/metadata/wrn3/WH7618/01-WH7618.zip"
ATTRIBUTION = "Contains data supplied by Rothamsted Research."
ACKNOWLEDGEMENT = (
    "The Electronic Rothamsted Archive (e-RA), its datasets, information and other resources, "
    "are part of the Rothamsted Long-Term Experiments - National Bioscience Research Infrastructure "
    "(RLTE-NBRI), funded by the UK Research and Innovation - Biotechnology and Biological Sciences "
    "Research Council (UKRI-BBSRC) under award BBS/E/RH/23NB0007 (2023-2028). "
    "The RLTE-NBRI is also supported by the Lawes Agricultural Trust."
)
CITATION = (
    "Glendining, M., Poulton, P., Macdonald, A., MacLaren, C., Clark, S. (2022). "
    "Woburn Ley-arable experiment: yields of wheat as first test crop, 1976-2018. "
    "Electronic Rothamsted Archive, Rothamsted Research. https://doi.org/" + DOI
)


def acquire_woburn(output):
    raw = output / "raw"
    landing = archive_response(LANDING, raw)
    terms = archive_response("https://www.era.rothamsted.ac.uk/info/conditions", raw)
    data = archive_response(DOWNLOAD, raw)
    manifest = {"landing": landing, "terms": terms, "data": data,
                "attribution": ATTRIBUTION, "acknowledgement": ACKNOWLEDGEMENT,
                "citation": CITATION, "license": "CC-BY-4.0"}
    path = output / (data["request_id"] + ".trial.json")
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def workbook_rows(payload, sheet):
    """Read original XLSX cell text without coercing source plot codes to floats."""
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        strings = ["".join(t.text or "" for t in node.findall(".//x:t", ns))
                   for node in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("x:si", ns)]
        root = ET.fromstring(archive.read(f"xl/worksheets/sheet{sheet}.xml"))
        result = []
        for row in root.findall("x:sheetData/x:row", ns):
            cells = {}
            for cell in row.findall("x:c", ns):
                value = cell.find("x:v", ns)
                if value is not None:
                    cells[cell.get("r")] = strings[int(value.text)] if cell.get("t") == "s" else value.text
            result.append(cells)
        return result


def read_woburn(manifest_path):
    manifest = json.loads(manifest_path.read_bytes())
    asset = manifest["data"]
    payload = Path(asset["raw_path"]).read_bytes()
    if sha256(payload).hexdigest() != asset["raw_sha256"]:
        raise ValueError("Empirical trial archive checksum mismatch")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        prefix = "01-WRN3-WH7618/"
        package = json.loads(archive.read(prefix + "datapackage.json"))
        if package["id"] != DOI or package["version"] != "1.0.0":
            raise ValueError("Unreviewed trial dataset/version")
        if not any(item["name"] == "CC-BY-4.0" for item in package["licenses"]):
            raise ValueError("Unexpected dataset license; review before import")
        resources = {}
        for resource in package["resources"]:
            content = archive.read(prefix + resource["path"])
            if md5(content).hexdigest() != resource["stats"]["hash"]:
                raise ValueError("Provider resource checksum mismatch")
            rows = list(csv.DictReader(StringIO(content.decode(resource["encoding"]))))
            if len(rows) != resource["stats"]["rows"]:
                raise ValueError("Provider resource row count mismatch")
            if rows and list(rows[0]) != [field["name"] for field in resource["schema"]["fields"]]:
                raise ValueError("Provider CSV fields differ from published schema")
            resources[resource["name"]] = {"schema": resource, "rows": rows}
        metadata_rows = workbook_rows(archive.read("01-WRN3-WH7618.xlsx"), 2)
        yield_rows = [row for row in metadata_rows if "grain_yield" in row.values()]
        if len(yield_rows) != 1 or "t ha-1 yr-1" not in yield_rows[0].values():
            raise ValueError("Cannot independently resolve original workbook yield unit")
    return manifest, package, resources, yield_rows[0]


def _date(value):
    return None if value in ("", "*") else date.fromisoformat(value)


def import_woburn(store, manifest_path):
    manifest, package, resources, unit_evidence = read_woburn(manifest_path)
    asset = manifest["data"]
    crop = "era:wheat"
    trial = "era:W/RN/3"
    notes = {row["note_id"]: row["description"] for row in resources["notes_data"]["rows"]}
    rotation_codes = {row["factor_level_name"] for row in resources["rotation_factor_data"]["rows"]}
    store.migrate()
    imported, missing, review = 0, 0, 0
    with store.session() as connection:
        connection.execute(
            "INSERT INTO source_assets VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (asset["raw_sha256"], asset["raw_sha256"], asset["raw_path"], asset["response_url"],
             asset["retrieved_at"], Jsonb(manifest)),
        )
        connection.execute("INSERT INTO crop_species VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                           (crop, "wheat", asset["raw_sha256"], Jsonb({"identity_basis": DOI, "taxonomy_review": "pending"})))
        connection.execute("INSERT INTO crop_trials VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                           (trial, asset["raw_sha256"], "era:Woburn", package["title"],
                            Jsonb({"doi": DOI, "version": package["version"], "attribution": ATTRIBUTION,
                                   "acknowledgement": ACKNOWLEDGEMENT, "citation": CITATION,
                                   "license": "CC-BY-4.0", "independent_sites": 1})))
        for name, resource in resources.items():
            connection.execute("INSERT INTO trial_resources VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                               (asset["raw_sha256"], name, Jsonb(resource["schema"]), Jsonb(resource["rows"])))
        seen = set()
        plot_codes = Counter((row["year"], row["plot_code"]) for row in resources["crop_data"]["rows"])
        for index, row in enumerate(resources["crop_data"]["rows"], 2):
            context_id = fingerprint([DOI, row["year"], row["block"], row["main_plot"], row["split_plot"]])
            if context_id in seen:
                raise ValueError("Duplicate trial plot/year in the original resource")
            seen.add(context_id)
            if row["rotation_factor_level"] not in rotation_codes:
                raise ValueError("Unresolved source rotation factor")
            cultivar = "era:cultivar:" + fingerprint([crop, row["cultivar"]])
            connection.execute("INSERT INTO crop_varieties VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                               (cultivar, crop, row["cultivar"], asset["raw_sha256"]))
            value = None if row["grain_yield"] in ("", "*") else float(Decimal(row["grain_yield"]) * 1000)
            note = (None if row["note_id"] in ("", "*") else
                    [{"note_id": key.strip(), "description": notes[key.strip()]}
                     for key in row["note_id"].split(",")])
            ambiguous_plot_code = plot_codes[(row["year"], row["plot_code"])] > 1
            availability = ("missing" if value is None else "requires_review"
                            if note or ambiguous_plot_code else "available_from_source")
            missing += value is None
            review += note is not None
            context = {
                "block": row["block"], "main_plot": row["main_plot"], "split_plot": row["split_plot"],
                "rotation_factor_level": row["rotation_factor_level"],
                "previous_FYM_factor_level": row["previous_FYM_factor_level"],
                "N_factor_level": row["N_factor_level"], "N_factor_code": row["N_factor_code"],
                "nitrogen_applied_original": row["N_fertilizer_amount"],
                "source_note": note, "source_unit": "t ha-1 yr-1",
                "source_plot_code_not_unique": ambiguous_plot_code,
                "identity_basis": "original year/block/main_plot/split_plot, not potentially duplicated plot_code",
                "conversion": "tonnes to kg: multiply by 1000; one recorded harvest-year outcome",
                "unit_evidence_workbook_cells": unit_evidence,
                "decision_at": None, "previous_crop_sequence": None,
                "limitations": [
                    "Rotation code retained; time-varying factor history requires explicit review",
                    "Sowing date is not evidence of a decision timestamp",
                    "Actual fertilizer use is not assumed known at planting",
                    "One UK site; not evidence of Karnataka/general crop suitability",
                    "2015 spring-wheat replacement and all source notes require review",
                ],
            }
            outcome_id = fingerprint([context_id, row, package["version"]])
            inserted = connection.execute(
                "INSERT INTO crop_performance "
                "(outcome_id,context_id,trial_id,crop_id,cultivar_id,source_asset_id,source_record_locator,"
                "harvest_year,plot_id,main_plot_id,rotation_code,sowing_date,harvest_date,yield_kg_ha,"
                "mass_basis,availability,raw_record,record_context) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (outcome_id, context_id, trial, crop, cultivar, asset["raw_sha256"],
                 f"01-WRN3-WH7618/crop_data.csv:row:{index}", int(row["year"]),
                 row["plot_code"], row["main_plot"], row["rotation_factor_level"],
                 _date(row["sow_date"]), _date(row["harvest_date"]), value,
                 "85_percent_dry_matter", availability, Jsonb(row), Jsonb(context)),
            ).rowcount
            imported += inserted
    with store.session() as connection:
        count = connection.execute("SELECT count(*) FROM crop_performance WHERE source_asset_id=%s",
                                   (asset["raw_sha256"],)).fetchone()[0]
        if count != len(seen):
            raise ValueError("Independent persisted trial row count differs")
    return {"inserted": imported, "persisted": count, "missing_yields": missing,
            "rows_with_notes": review, "training_ready": False, "doi": DOI,
            "attribution": ATTRIBUTION, "acknowledgement": ACKNOWLEDGEMENT, "citation": CITATION}
