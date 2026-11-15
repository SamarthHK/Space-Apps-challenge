"""Versioned EcoCrop assertions, not observed outcomes or India-presence labels."""

import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, FiniteFloat, model_validator
import yaml

from .assets import archive_response
from .model_records import model_record, persist_model_bundle, source_evidence
from .outcome_data import checked_bytes, write_json
from .source_tables import SourceHTML
from .storage_proof import require


BASE = "https://ecocrop.apps.fao.org/ecocrop/srv/en/"
MISSING = {"", "-", "---", "no input"}
NUMERIC = {
    "Temperat. requir.": ("temperature", "degC", "growing_season", "2000"),
    "Rainfall (annual)": ("annual_water", "mm/year", "annual", "2001"),
    "Soil PH": ("soil_ph", "1", "soil_reference", "2005"),
    "Altitude": ("altitude", "m", "static_reference", "2003"),
}
DEFINITIONS = {
    "2000": ("temperature", "growing season"),
    "2001": ("annual rainfall", "irrigation"),
    "2003": ("meter above sea level",),
    "2004": ("annual crops", "number of days"),
    "2005": ("soil ph",),
}
CATEGORIES = {
    "Soil depth": "soil_depth", "Soil texture": "soil_texture",
    "Soil fertility": "soil_fertility", "Soil salinity": "soil_salinity",
    "Soil drainage": "soil_drainage",
}


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: Literal["fao_ecocrop"] = "fao_ecocrop"
    source_crop_id: str
    metric_id: str
    evidence_type: Literal["published_parameter"] = "published_parameter"
    value_type: Literal["numeric_range", "numeric_interval", "categories", "text", "unresolved"]
    unit: str
    temporal_support: str
    availability: Literal["available", "partial", "missing", "unresolved"]
    optimal_min: FiniteFloat | None = None
    optimal_max: FiniteFloat | None = None
    absolute_min: FiniteFloat | None = None
    absolute_max: FiniteFloat | None = None
    minimum: FiniteFloat | None = None
    maximum: FiniteFloat | None = None
    categories: dict[str, str | None] | None = None
    value_text: str | None = None
    limitation: str | None = None

    @model_validator(mode="after")
    def validate_ranges(self):
        for low, high in ((self.optimal_min, self.optimal_max), (self.absolute_min, self.absolute_max),
                          (self.absolute_min, self.optimal_min), (self.optimal_max, self.absolute_max),
                          (self.minimum, self.maximum)):
            if low is not None and high is not None and low > high:
                raise ValueError("Source requirement ranges are inconsistent")
        if self.value_type in ("numeric_range", "numeric_interval"):
            values = ([self.optimal_min, self.optimal_max, self.absolute_min, self.absolute_max]
                      if self.value_type == "numeric_range" else [self.minimum, self.maximum])
            count = sum(value is not None for value in values)
            expected = "missing" if count == 0 else "available" if count == len(values) else "partial"
            if self.availability != expected or self.categories is not None or self.value_text is not None:
                raise ValueError("Requirement availability/value representation is inconsistent")
        elif self.value_type == "categories":
            if not self.categories:
                raise ValueError("A category requirement needs its named source categories")
            count = sum(value is not None for value in self.categories.values())
            expected = "missing" if count == 0 else "available" if count == len(self.categories) else "partial"
            if self.availability != expected:
                raise ValueError("Category requirement availability is inconsistent")
        elif self.value_type == "text":
            if self.availability != ("missing" if self.value_text is None else "available"):
                raise ValueError("Text requirement availability is inconsistent")
        return self


def _text(value):
    value = " ".join(value.split())
    return None if value.casefold() in MISSING else value


def _number(value):
    value = _text(value)
    if value is None:
        return None
    require(bool(re.fullmatch(r"-?\d+(?:\.\d+)?", value)), "Unrecognized numeric source requirement")
    return float(value)


def acquire_crop_profiles(contract_path, output):
    config = yaml.safe_load(Path(contract_path).read_bytes())
    require(config["schema_version"] == "1", "Unsupported India contract version")
    identifiers = [str(value) for value in config["profile_ids"]]
    require(identifiers and len(set(identifiers)) == len(identifiers), "Repeated or absent crop profile IDs")
    require(all(re.fullmatch(r"[1-9]\d*", value) for value in identifiers), "Invalid EcoCrop identifier")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    corpus = {"schema_version": "1", "kind": "ecocrop_profile_corpus",
              "assets": [], "profiles": {}, "definitions": {}, "status": "in_progress"}
    try:
        for identifier in DEFINITIONS:
            asset = archive_response(BASE + "helpShow", output / "raw", {"id": identifier})
            corpus["assets"].append(asset)
            corpus["definitions"][identifier] = asset
        for identifier in identifiers:
            asset = archive_response(BASE + "dataSheet", output / "raw", {"id": identifier})
            corpus["assets"].append(asset)
            corpus["profiles"][identifier] = asset
        normalize_crop_profiles(corpus)
        corpus["status"] = "complete"
        write_json(output / "corpus.json", corpus)
        return output / "corpus.json"
    except Exception as error:
        corpus.update(status="failed", error_type=type(error).__name__)
        write_json(output / "corpus.json", corpus)
        raise


def normalize_crop_profiles(corpus):
    require(corpus["schema_version"] == "1" and corpus["kind"] == "ecocrop_profile_corpus",
            "Wrong crop profile corpus")
    for identifier, phrases in DEFINITIONS.items():
        body = checked_bytes(corpus["definitions"][identifier]).decode("utf-8")
        readable = " ".join(re.sub(r"<[^>]+>", " ", body).casefold().split())
        require(all(phrase in readable for phrase in phrases), "Crop requirement definition changed")
    records, evidence = [], []
    for identifier, asset in corpus["profiles"].items():
        document = SourceHTML(checked_bytes(asset).decode("utf-8"))
        require(document.inputs.get("id") == identifier, "Source profile identifier mismatch")
        names = [text for tag, text in document.headings if tag == "h2"]
        require(len(names) == 1 and bool(names[0]), "Missing or ambiguous crop identity")
        profile = model_record("crop_profile", ["fao_ecocrop", identifier, "identity"], {
            "source_id": "fao_ecocrop", "source_crop_id": identifier, "scientific_name": names[0],
            "evidence_type": "published_parameter", "geographic_scope": "global_reference",
            "india_presence": "not_verified",
        })
        records.append(profile)
        evidence.append(source_evidence(profile, asset, "h2"))
        ecology = [table for table in document.tables if table.rows and
                   [cell.text for cell in table.rows[0]] == ["Ecology"]]
        require(len(ecology) == 1, "Missing or ambiguous crop ecology table")
        rows = [[cell.text for cell in row] for row in ecology[0].rows]
        traits = []
        for label, (metric, unit, period, definition) in NUMERIC.items():
            found = [row for row in rows if row and row[0] == label]
            require(len(found) == 1 and len(found[0]) == 8, "Crop ecology row schema changed")
            bounds = [_number(value) for value in found[0][1:5]]
            count = sum(value is not None for value in bounds)
            traits.append((Requirement(
                source_crop_id=identifier, metric_id=metric, value_type="numeric_range", unit=unit,
                temporal_support=period, availability="missing" if count == 0 else "available" if count == 4 else "partial",
                **dict(zip(("optimal_min", "optimal_max", "absolute_min", "absolute_max"), bounds)),
                limitation="Supplemental water must have matching annual support." if metric == "annual_water" else None,
            ), label, definition))
        for label, metric in CATEGORIES.items():
            found = [row for row in rows if len(row) == 8 and row[5] == label]
            require(len(found) == 1, "Crop soil-category row schema changed")
            values = [_text(value) for value in found[0][6:8]]
            count = sum(value is not None for value in values)
            traits.append((Requirement(
                source_crop_id=identifier, metric_id=metric, value_type="categories", unit="category",
                temporal_support="soil_reference",
                availability="missing" if count == 0 else "available" if count == 2 else "partial",
                categories=dict(zip(("optimal", "absolute"), values)),
            ), label, None))
        for label, metric in (("Latitude", "latitude"), ("Light intensity", "light_intensity")):
            found = [row for row in rows if row and row[0] == label]
            require(len(found) == 1 and len(found[0]) == 8, "Crop reference row schema changed")
            values = [_text(value) for value in found[0][1:5]]
            count = sum(value is not None for value in values)
            traits.append((Requirement(
                source_crop_id=identifier, metric_id=metric, value_type="unresolved" if metric == "latitude" else "categories",
                unit="unresolved" if metric == "latitude" else "category", temporal_support="reference",
                availability="unresolved" if metric == "latitude" else
                "missing" if count == 0 else "available" if count == 4 else "partial",
                categories=dict(zip(("optimal_min", "optimal_max", "absolute_min", "absolute_max"), values)),
                limitation="Latitude bound orientation is not normalized." if metric == "latitude"
                else "Qualitative light classes are not quantitative solar radiation.",
            ), label, None))
        text_fields = {
            "Life form": ("life_form", "static_reference"),
            "Life span": ("biological_life_span", "static_reference"),
            "Physiology": ("physiology", "static_reference"),
            "Climate zone": ("climate_zone", "reference"),
            "Photoperiod": ("photoperiod", "growing_season"),
            "Killing temp. during rest": ("killing_temperature_rest", "dormancy"),
            "Killing temp. early growth": ("killing_temperature_early_growth", "early_growth"),
        }
        all_rows = [[cell.text for cell in row] for table in document.tables for row in table.rows]
        for label, (metric, period) in text_fields.items():
            found = [(row, index) for row in all_rows for index in (0, 2)
                     if len(row) > index + 1 and row[index] == label]
            require(len(found) == 1, "Crop descriptive row schema changed")
            value = _text(found[0][0][found[0][1] + 1])
            traits.append((Requirement(
                source_crop_id=identifier, metric_id=metric, value_type="text", unit="source_text",
                temporal_support=period, availability="missing" if value is None else "available", value_text=value,
                limitation="Source biology does not determine field occupancy or Indian production system."
                if metric == "biological_life_span" else None,
            ), label, None))
        cycles = [row for row in all_rows if len(row) == 5 and row[2] == "Crop cycle"]
        require(len(cycles) == 1, "Crop cycle row schema changed")
        low, high = map(_number, cycles[0][3:5])
        traits.append((Requirement(
            source_crop_id=identifier, metric_id="crop_cycle", value_type="numeric_interval", unit="day",
            temporal_support="source_cycle", availability="missing" if low is None and high is None else
            "available" if low is not None and high is not None else "partial",
            minimum=low, maximum=high,
            limitation="Not a planting-to-first-bearing duration; production-system scope must be resolved.",
        ), "Crop cycle", "2004"))
        for trait, locator, definition in traits:
            record = model_record("crop_requirement", ["fao_ecocrop", identifier, trait.metric_id],
                                  trait.model_dump(mode="json"))
            records.append(record)
            evidence.append(source_evidence(record, asset, locator))
            if definition:
                evidence.append(source_evidence(
                    record, corpus["definitions"][definition], "helpShow:" + definition, "definition"))
    return records, evidence


def build_crop_profiles(corpus_path, output, store):
    corpus = json.loads(Path(corpus_path).read_bytes())
    require(corpus["status"] == "complete", "Crop acquisition corpus is incomplete")
    records, evidence = normalize_crop_profiles(corpus)
    return persist_model_bundle(
        store, output, "crop_requirement_dataset",
        {"schema_version": "1", "source_id": "fao_ecocrop", "evidence_type": "published_parameter",
         "india_presence_verified": False, "observed_outcome_labels": False,
         "attribution": "FAO. EcoCrop.", "licence": "CC-BY-4.0",
         "licence_reference": "https://data.apps.fao.org/catalog/dataset/ecocrop"},
        corpus, records, evidence,
    )
