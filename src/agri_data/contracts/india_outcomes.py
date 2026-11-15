"""Official Indian district APY records with source units and reporting-period limits."""

from decimal import Decimal
import json
from pathlib import Path
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, FiniteFloat, model_validator
import yaml

from .assets import archive_response, system_trust_session
from .identity import fingerprint
from .model_records import model_record, persist_model_bundle, source_evidence
from .outcome_data import checked_bytes, write_json
from .source_tables import SourceHTML
from .storage_proof import require


BASE = "https://data.desagri.gov.in"
FORM_URL = BASE + "/website/crops-apy-report-web"
REPORT_URL = BASE + "/report/crop/horizontal_crop_vertical_year"
SELECTORS = {
    "states": "fltrstates[]", "crops": "fltrcrops[]", "seasons": "fltrseason[]",
    "start_year": "fltrstartyear", "end_year": "fltrendyear",
}
MISSING = {"", "-", "--", "*", "na", "n.a.", "not available"}


def name_key(value):
    return " ".join(value.casefold().split())


def report_name(value):
    return re.sub(r"^\d+\.\s*", "", value).strip()


def decimal_cell(value):
    text = value.strip()
    if text.casefold() in MISSING:
        return None, None
    require(bool(re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+|\d{1,2}(?:,\d{2})*,\d{3})(?:\.\d+)?", text)),
            "Unrecognized statistical value; original source retained")
    number = Decimal(text.replace(",", ""))
    return float(number), float(Decimal(1).scaleb(number.as_tuple().exponent))


class RegionalOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: Literal["india_des_apy"] = "india_des_apy"
    evidence_type: Literal["derived"] = "derived"
    reporting_basis: Literal["official_district_aggregate"] = "official_district_aggregate"
    source_state_id: str
    state_name: str
    district_name: str
    source_crop_id: str
    crop_name: str
    source_season_id: str
    season_name: str
    reporting_year_start: int
    reporting_year_end: int
    source_year_label: str
    area: FiniteFloat | None
    area_unit: str
    production: FiniteFloat | None
    production_unit: str
    reported_yield: FiniteFloat | None
    reported_yield_unit: str
    display_precision: dict[str, float | None]
    arithmetic_status: Literal["consistent", "inconsistent", "missing", "nonpositive_area", "unresolved_units"]
    product_basis: Literal["as_reported_not_fully_specified"] = "as_reported_not_fully_specified"
    exact_sowing_date: None = None
    exact_harvest_date: None = None
    historical_available_at: None = None
    boundary_vintage: None = None

    @model_validator(mode="after")
    def check_year(self):
        if self.reporting_year_end != self.reporting_year_start + 1:
            raise ValueError("Source agricultural-year label is inconsistent")
        return self


def read_form(asset):
    document = SourceHTML(checked_bytes(asset).decode("utf-8"))
    options = {}
    for key, name in SELECTORS.items():
        values = [(identifier, label) for identifier, label in document.selects.get(name, []) if identifier]
        require(values and len({identifier for identifier, _ in values}) == len(values),
                "Missing or ambiguous official report selector")
        require(len({name_key(label) for _, label in values}) == len(values), "Ambiguous source labels")
        options[key] = dict(values)
    return document, options


def _arithmetic(values, units, precision):
    if any(value is None for value in values):
        return "missing"
    area, production, reported = values
    if area <= 0:
        return "nonpositive_area"
    if [name_key(unit) for unit in units] != ["hectare", "tonnes", "tonne/hectare"]:
        return "unresolved_units"
    if production < 0 or reported < 0:
        return "inconsistent"
    da, dp, dy = [value / 2 for value in precision]
    if area <= da:
        return "inconsistent"
    low = max(0, production - dp) / (area + da)
    high = (production + dp) / (area - da)
    return "consistent" if reported + dy >= low - 1e-12 and reported - dy <= high + 1e-12 else "inconsistent"


def normalize_report(asset, form_asset, selection):
    _, options = read_form(form_asset)
    lookup = {key: {name_key(label): identifier for identifier, label in options[key].items()}
              for key in ("states", "crops", "seasons")}
    document = SourceHTML(checked_bytes(asset).decode("utf-8"))
    rows = document.table("apyreport").grid()
    require(len(rows) >= 3 and len(rows[0]) >= 6 and (len(rows[0]) - 3) % 3 == 0,
            "Unexpected official APY table dimensions")
    require(all(row[:3] == ["State", "District", "Year"] for row in rows[:3]),
            "Unexpected official APY table header")
    columns = []
    for index in range(3, len(rows[0]), 3):
        require(len(set(rows[0][index:index + 3])) == len(set(rows[1][index:index + 3])) == 1,
                "Mixed crop/season columns in source table")
        crop_name, season_name = rows[0][index], rows[1][index]
        require(name_key(crop_name) in lookup["crops"] and name_key(season_name) in lookup["seasons"],
                "Report crop or season is absent from source catalogue")
        crop, season = lookup["crops"][name_key(crop_name)], lookup["seasons"][name_key(season_name)]
        require(crop in selection["crops"] and season in selection["seasons"],
                "Report contains an unrequested crop or season")
        units = []
        for expected, label in zip(("Area", "Production", "Yield"), rows[2][index:index + 3]):
            matched = re.fullmatch(expected + r"\s*\(([^)]+)\)", label)
            require(matched is not None, "Source metric/unit header changed")
            units.append(matched[1])
        columns.append((index, crop, crop_name, season, season_name, units))
    records, evidence = [], []
    for row_index, cells in enumerate(rows[3:], 4):
        state_name, district_name = map(report_name, cells[:2])
        require(name_key(state_name) in lookup["states"] and district_name, "Unknown state/district in report")
        state = lookup["states"][name_key(state_name)]
        require(state in selection["states"], "Report contains an unrequested state")
        year = re.fullmatch(r"(\d{4})\s*[-\u2013]\s*(\d{4})", cells[2])
        require(year is not None, "Unknown agricultural-year format")
        start, end = int(year[1]), int(year[2])
        require(selection["start_year"] <= start <= selection["end_year"], "Report year is outside requested interval")
        support = "des-district-" + fingerprint([state, name_key(district_name)])
        for index, crop, crop_name, season, season_name, units in columns:
            pairs = [decimal_cell(value) for value in cells[index:index + 3]]
            values, precision = [pair[0] for pair in pairs], [pair[1] for pair in pairs]
            if all(value is None for value in values):
                continue
            outcome = RegionalOutcome(
                source_state_id=state, state_name=state_name, district_name=district_name,
                source_crop_id=crop, crop_name=crop_name, source_season_id=season, season_name=season_name,
                reporting_year_start=start, reporting_year_end=end, source_year_label=cells[2],
                area=values[0], area_unit=units[0], production=values[1], production_unit=units[1],
                reported_yield=values[2], reported_yield_unit=units[2],
                display_precision=dict(zip(("area", "production", "reported_yield"), precision)),
                arithmetic_status=_arithmetic(values, units, precision),
            )
            record = model_record("regional_outcome", ["india_des_apy", support, crop, season, start, end],
                                  outcome.model_dump(mode="json"), support)
            records.append(record)
            evidence.append(source_evidence(record, asset, f"table#apyreport:row:{row_index}:columns:{index + 1}-{index + 3}"))
            evidence.append(source_evidence(record, form_asset, "form:state-crop-season-year-codes", "definition"))
    require(len({row["context_id"] for row in records}) == len(records), "Duplicate district/crop/season/year in source report")
    return records, evidence


def acquire_india_outcomes(contract_path, output):
    config = yaml.safe_load(Path(contract_path).read_bytes())
    require(config["schema_version"] == "1", "Unsupported India contract version")
    spec = config["des"]
    require(isinstance(spec["years_per_request"], int) and 1 <= spec["years_per_request"] <= 5,
            "Public report requests must use bounded year batches")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    corpus = {"schema_version": "1", "kind": "india_des_apy_corpus", "status": "in_progress",
              "assets": [], "reports": [], "selection": spec}
    try:
        with system_trust_session() as session:
            form = archive_response(FORM_URL, output / "raw", session=session)
            corpus["assets"].append(form)
            corpus["form"] = form
            document, options = read_form(form)
            require(document.inputs.get("_token"), "Public form session token is absent")
            for key in ("states", "crops", "seasons"):
                require(spec[key] and len(set(spec[key])) == len(spec[key])
                        and set(spec[key]) <= options[key].keys(), "Invalid or repeated official source selection")
            for key in ("start_year", "end_year"):
                require(str(spec[key]) in options[key], "Year is absent from official source catalogue")
            require(spec["start_year"] <= spec["end_year"], "Reversed source reporting years")
            for state in spec["states"]:
                for start in range(spec["start_year"], spec["end_year"] + 1, spec["years_per_request"]):
                    end = min(start + spec["years_per_request"] - 1, spec["end_year"])
                    selection = {"states": [state], "crops": spec["crops"], "seasons": spec["seasons"],
                                 "start_year": start, "end_year": end}
                    asset = archive_response(
                        REPORT_URL, output / "raw", session=session, method="POST", timeout=180,
                        data={"reportformat": "horizontal_crop_vertical_year", "fltrstates[]": [state],
                              "fltrdistricts[]": [""], "fltrcrops[]": spec["crops"], "fltrseason[]": spec["seasons"],
                              "fltrstartyear": str(start), "fltrendyear": str(end), "fltrrptformat": "scrview",
                              "_token": document.inputs["_token"]},
                    )
                    corpus["assets"].append(asset)
                    records, _ = normalize_report(asset, form, selection)
                    corpus["reports"].append({"asset": asset, "selection": selection, "record_count": len(records)})
                    write_json(output / "corpus.json", corpus)
        corpus["status"] = "complete"
        write_json(output / "corpus.json", corpus)
        return output / "corpus.json"
    except Exception as error:
        corpus.update(status="failed", error_type=type(error).__name__)
        write_json(output / "corpus.json", corpus)
        raise


def build_india_outcomes(corpus_path, output, store):
    corpus = json.loads(Path(corpus_path).read_bytes())
    require(corpus["schema_version"] == "1" and corpus["kind"] == "india_des_apy_corpus"
            and corpus["status"] == "complete", "Indian outcome acquisition is incomplete or incompatible")
    records, evidence = [], []
    for entry in corpus["reports"]:
        batch, proof = normalize_report(entry["asset"], corpus["form"], entry["selection"])
        require(len(batch) == entry["record_count"], "Source report count changed")
        records.extend(batch)
        evidence.extend(proof)
    return persist_model_bundle(
        store, output, "india_regional_outcome_dataset",
        {"schema_version": "1", "source_id": "india_des_apy", "geographic_scope": "reported_districts",
         "temporal_support": "source_agricultural_year_and_season", "exact_crop_dates_available": False,
         "historical_availability_verified": False, "field_observations": False,
         "units": "source_headers", "derivation": "parse_and_reconcile_reported_APY",
         "attribution": "Directorate of Economics and Statistics, Department of Agriculture and Farmers Welfare, Government of India.",
         "licence": "redistribution_terms_not_verified", "source_reference": FORM_URL},
        corpus, records, evidence,
    )
