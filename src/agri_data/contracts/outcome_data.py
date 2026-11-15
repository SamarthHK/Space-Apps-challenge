"""Authentic multicrop records and matched weather for retrospective experiments."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import uuid

import pandas as pd
from psycopg.types.json import Jsonb
import yaml

from .assets import archive_response
from .identity import fingerprint
from .power import normalize_power, PARAMETERS
from .storage_proof import require
from .trials import acquire_woburn, read_woburn, ATTRIBUTION, ACKNOWLEDGEMENT, CITATION, DOI


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def load_config(path):
    config = yaml.safe_load(path.read_bytes())
    require(config["schema_version"] == "1" and config["task"] == "retrospective_preplant_crop_outcome",
            "Unexpected outcome-model contract")
    require(0 < config["weather"]["minimum_coverage"] <= 1, "Invalid coverage threshold")
    require(all(isinstance(n, int) and n > 0 for n in config["weather"]["windows_days"]),
            "Weather windows must be positive day counts")
    weather = config["weather"]
    require(date.fromisoformat(weather["start"]) <= date.fromisoformat(weather["end"]),
            "Reversed weather date interval")
    evaluation = config["evaluation"]
    require(0 < evaluation["train_fraction"] < 1 and 0 < evaluation["validation_fraction"] < 1
            and evaluation["train_fraction"] + evaluation["validation_fraction"] < 1,
            "Evaluation fractions must reserve a test partition")
    require(len({s["id"] for s in config["sources"]}) == len(config["sources"]), "Duplicate source IDs")
    require(weather["time_standard"] == "LST", "This retrospective cutoff currently requires provider LST days")
    return config


def acquire_outcome_corpus(config_path, output):
    config = load_config(config_path)
    output.mkdir(parents=True, exist_ok=True)
    run = {"schema_version": "1", "config": config, "assets": [], "sources": [], "weather": {}}
    manifest_path = output / (uuid.uuid4().hex + ".corpus.json")
    try:
        terms = archive_response("https://www.era.rothamsted.ac.uk/info/conditions", output / "raw")
        run["assets"].append(terms)
        for name, site in config["sites"].items():
            asset = archive_response(site["reference"], output / "raw")
            text = Path(asset["raw_path"]).read_text(encoding="utf-8")
            require(f"{site['latitude']},{site['longitude']}" in text,
                    f"{name}: coordinates are not present in the official site reference")
            run["assets"].append(asset)
        for source in config["sources"]:
            landing = archive_response(source["landing"], output / "raw")
            text = Path(landing["raw_path"]).read_text(encoding="utf-8")
            require(source["doi"].lower() in text.lower() and "creativecommons.org/licenses/by/4.0" in text,
                    "Dataset identity/license changed")
            require(source["download"] in text, "Download is not linked by the official page")
            asset = archive_response(source["download"], output / "raw")
            run["assets"].extend([landing, asset])
            run["sources"].append({"spec": source, "asset": asset})
        woburn = acquire_woburn(output / "woburn")
        run["woburn_manifest"] = str(woburn.resolve())
        run["assets"].extend(json.loads(woburn.read_bytes())[key] for key in ("landing", "terms", "data"))
        for name, site in config["sites"].items():
            asset = archive_response(
                "https://power.larc.nasa.gov/api/temporal/daily/point", output / "raw",
                {"latitude": site["latitude"], "longitude": site["longitude"],
                 "start": config["weather"]["start"].replace("-", ""),
                 "end": config["weather"]["end"].replace("-", ""),
                 "parameters": ",".join(PARAMETERS), "community": "AG", "format": "JSON",
                 "time-standard": config["weather"]["time_standard"]},
                timeout=180,
            )
            run["assets"].append(asset)
            run["weather"][name] = asset
        run["status"] = "complete"
        write_json(manifest_path, run)
        return manifest_path
    except Exception as error:
        run.update(status="failed", error_type=type(error).__name__)
        write_json(manifest_path, run)
        raise


def checked_bytes(asset):
    payload = Path(asset["raw_path"]).read_bytes()
    require(sha256(payload).hexdigest() == asset["raw_sha256"], "Source checksum mismatch")
    return payload


def source_date(value):
    if value is None or str(value).strip() in ("", "*"):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    try:
        return datetime.fromisoformat(str(value)).date().isoformat()
    except ValueError:
        return None


def number(value):
    if value is None or str(value).strip() in ("", "*"):
        return None
    try:
        value = float(Decimal(str(value)))
    except Exception:
        return None
    return value if math.isfinite(value) else None


def _json_value(value):
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def workbook_tables(asset):
    from openpyxl import load_workbook
    book = load_workbook(BytesIO(checked_bytes(asset)), read_only=True, data_only=True)
    try:
        result = {}
        for sheet in book:
            if sheet.title == "README":
                continue
            iterator = sheet.values
            headers = next(iterator)
            names = [str(h).strip() for h in headers if h is not None]
            require(len(names) == len(set(names)), "Duplicate spreadsheet columns")
            result[sheet.title] = [
                {str(key).strip(): _json_value(value) for key, value in zip(headers, row) if key is not None}
                for row in iterator if any(value is not None for value in row)
            ]
        return result
    finally:
        book.close()


def read_broadbalk(entry):
    spec, asset = entry["spec"], entry["asset"]
    tables = workbook_tables(asset)
    metadata = [row for row in tables["fields_metadata"]
                if row.get("resource") == "yield_data" and row.get("name") == spec["target_column"]]
    require(len(metadata) == 1 and metadata[0].get(
        "measurement_unit", metadata[0].get("measurementUnit")) == spec["target_unit"],
            "Unexpected target field/unit in workbook")
    notes = {str(int(row["notes_id"])): row["description"] for row in tables["notes_data"]
             if row.get("notes_id") is not None}
    rows = []
    for index, raw in enumerate(tables["yield_data"], 2):
        require(all(key in raw for key in (
            "plot", "harvest_year", "previous_crop", spec["crop_column"], spec["target_column"],
            spec["sowing_column"], "harvest_date", "cultivar",
        )), "Source schema is missing required outcome columns")
        value = number(raw[spec["target_column"]])
        original_note = raw.get("note")
        note_ids = [] if original_note is None else str(original_note).replace(" ", "").split(",")
        note_text = [notes.get(key, f"Unresolved source note {key}") for key in note_ids]
        raw_crop = str(raw[spec["crop_column"]])
        strip = str(raw["strip"])
        # Provider notes identify these as the same strips, not new plots.
        strip = {"2.1": "21", "2.2": "22"}.get(strip, strip)
        plot = strip + "\\" + str(raw["section"])
        context = [spec["site"], plot, str(raw["harvest_year"])]
        record = {
            "context_id": fingerprint(context), "site_id": spec["site"], "crop_id": spec["crop"],
            "plot_id": plot, "original_plot_id": str(raw["plot"]),
            "group_id": fingerprint([spec["site"], strip]), "harvest_year": int(raw["harvest_year"]),
            "crop_form": raw_crop, "previous_crop": raw["previous_crop"],
            "cultivar": raw["cultivar"], "rotation_code": None,
            "sowing_date": source_date(raw[spec["sowing_column"]]),
            "harvest_date": source_date(raw["harvest_date"]),
            "yield_kg_ha": value * 1000 if value is not None else None,
            "mass_basis": spec["mass_basis"], "target_unit": "kg/ha",
            "original_unit": spec["target_unit"], "source_asset_id": asset["raw_sha256"],
            "source_locator": f"yield_data:row:{index}", "doi": spec["doi"],
            "source_notes": note_text, "raw_record": raw,
        }
        record["record_id"] = fingerprint(record)
        rows.append(record)
    return rows, tables


def read_woburn_outcomes(path):
    manifest, package, resources, unit = read_woburn(path)
    notes = {r["note_id"]: r["description"] for r in resources["notes_data"]["rows"]}
    result = []
    for index, raw in enumerate(resources["crop_data"]["rows"], 2):
        value = number(raw["grain_yield"])
        context = ["woburn", raw["year"], raw["block"], raw["main_plot"], raw["split_plot"]]
        record = {
            "context_id": fingerprint(context), "site_id": "woburn", "crop_id": "wheat",
            "plot_id": "|".join(context[2:]), "harvest_year": int(raw["year"]),
            "original_plot_id": raw["plot_code"],
            "group_id": fingerprint(["woburn", raw["block"], raw["main_plot"]]),
            "crop_form": "spring wheat" if raw["year"] == "2015" else "winter wheat",
            "previous_crop": None, "cultivar": raw["cultivar"], "rotation_code": raw["rotation_factor_level"],
            "sowing_date": source_date(raw["sow_date"]), "harvest_date": source_date(raw["harvest_date"]),
            "yield_kg_ha": value * 1000 if value is not None else None,
            "mass_basis": "grain_85_percent_dry_matter", "target_unit": "kg/ha",
            "original_unit": "t ha-1 yr-1", "source_asset_id": manifest["data"]["raw_sha256"],
            "source_locator": f"crop_data.csv:row:{index}", "doi": DOI,
            "source_notes": [notes[key.strip()] for key in raw["note_id"].split(",")]
                if raw["note_id"] not in ("", "*") else [],
            "raw_record": raw,
        }
        record["record_id"] = fingerprint(record)
        result.append(record)
    return result, resources


def read_weather(asset, site, config):
    raw = json.loads(checked_bytes(asset))
    require(raw["header"]["start"] == config["weather"]["start"].replace("-", "")
            and raw["header"]["end"] == config["weather"]["end"].replace("-", ""),
            "Weather response dates differ from requested dates")
    require(raw["header"]["time_standard"] == config["weather"]["time_standard"], "Weather time standard mismatch")
    expected = config["sites"][site]
    coordinates = raw["geometry"]["coordinates"]
    require(abs(coordinates[0] - expected["longitude"]) <= 0.01
            and abs(coordinates[1] - expected["latitude"]) <= 0.01, "Weather location mismatch")
    observations, missing, metadata = normalize_power(asset, site)
    rows = {}
    for observation in observations:
        day = observation.observed_at.date().isoformat()
        rows.setdefault(day, {})[observation.variable_id] = observation.value_numeric
    days = pd.date_range(config["weather"]["start"], config["weather"]["end"])
    records = []
    for timestamp in days:
        day = timestamp.date().isoformat()
        record = {"site_id": site, "date": day,
                  **{variable: rows.get(day, {}).get(variable) for variable, _, _ in PARAMETERS.values()},
                  "source_asset_id": asset["raw_sha256"], "context_id": fingerprint([site, day]),
                  "source_locator": f"/properties/parameter/*/{day.replace('-', '')}"}
        record["record_id"] = fingerprint(record)
        records.append(record)
    return records


def build_outcome_dataset(corpus_path, output, store):
    output.mkdir(parents=True, exist_ok=False)
    try:
        corpus = json.loads(corpus_path.read_bytes())
        require(corpus["status"] == "complete", "Acquisition corpus is incomplete")
        for asset in corpus["assets"]:
            checked_bytes(asset)
        outcomes, references = [], {}
        for entry in corpus["sources"]:
            rows, tables = read_broadbalk(entry)
            outcomes.extend(rows)
            references[entry["spec"]["id"]] = {k: v for k, v in tables.items() if k != "yield_data"}
        rows, references["woburn"] = read_woburn_outcomes(Path(corpus["woburn_manifest"]))
        outcomes.extend(rows)
        contexts = {}
        for record in outcomes:
            require(record["context_id"] not in contexts, "Duplicate or conflicting crop-season context")
            contexts[record["context_id"]] = record
        weather = []
        for site, asset in corpus["weather"].items():
            weather.extend(read_weather(asset, site, corpus["config"]))
        records = [("crop_outcome", r) for r in outcomes] + [("weather_day", r) for r in weather]
        identifier = fingerprint({"record_ids": sorted(r["record_id"] for _, r in records),
                                  "config": corpus["config"]})
        store.migrate()
        with store.session() as connection:
            for asset in corpus["assets"]:
                connection.execute(
                    "INSERT INTO source_assets VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (asset["raw_sha256"], asset["raw_sha256"], asset["raw_path"],
                     asset["response_url"], asset["retrieved_at"], Jsonb(asset)),
                )
            connection.execute("INSERT INTO model_datasets(dataset_id,manifest) VALUES(%s,%s) ON CONFLICT DO NOTHING",
                               (identifier, Jsonb(corpus)))
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO model_source_records VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    [(r["record_id"], r["context_id"], kind, r["site_id"], r["source_asset_id"], Jsonb(r))
                     for kind, r in records],
                )
                cursor.executemany(
                    "INSERT INTO model_dataset_records VALUES(%s,%s) ON CONFLICT DO NOTHING",
                    [(identifier, r["record_id"]) for _, r in records],
                )
        with store.session(repeatable_read=True) as connection:
            restored = connection.execute(
                "SELECT r.record_kind,r.record FROM model_source_records r JOIN model_dataset_records d "
                "USING(record_id) WHERE d.dataset_id=%s ORDER BY r.record_id", (identifier,),
            ).fetchall()
        require({r["record_id"]: r for _, r in restored} == {r["record_id"]: r for _, r in records},
                "Persisted model records differ from source-normalized records")
        for kind, filename in (("crop_outcome", "outcomes"), ("weather_day", "weather")):
            rows = []
            for row_kind, record in restored:
                if row_kind != kind:
                    continue
                rows.append({k: json.dumps(v, sort_keys=True) if isinstance(v, (dict, list)) else v
                             for k, v in record.items()})
            table = pd.DataFrame(rows)
            path = output / (filename + ".parquet")
            table.to_parquet(path, index=False)
            require(pd.read_parquet(path).to_json(orient="records", double_precision=15)
                    == table.to_json(orient="records", double_precision=15), "Parquet values differ from SQL readback")
        write_json(output / "references.json", references)
        write_json(output / "corpus.json", corpus)
        manifest = {
            "schema_version": "1", "kind": "retrospective_outcome_dataset", "dataset_id": identifier,
            "counts": {"outcomes": len(outcomes), "weather_days": len(weather),
                       "crops": sorted({r["crop_id"] for r in outcomes}),
                       "sites": sorted(corpus["weather"])},
            "attribution": ATTRIBUTION, "acknowledgement": ACKNOWLEDGEMENT,
            "citations": [CITATION] + [s["citation"] for s in corpus["config"]["sources"]],
            "files": {p.name: sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        }
        write_json(output / "manifest.json", manifest)
        return manifest
    except Exception as error:
        write_json(output / "failure.json", {"status": "failed", "error_type": type(error).__name__})
        raise
