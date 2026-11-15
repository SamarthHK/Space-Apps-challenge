"""Acquire published GAEZ targets and covariates without manufacturing crop examples."""

from collections import Counter
import json
from pathlib import Path
from urllib.parse import quote

import numpy as np
from openpyxl import load_workbook
import rasterio
from rasterio.transform import Affine
from rasterio.windows import Window
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep
import yaml

from .assets import archive_response, system_trust_session
from .identity import fingerprint
from .model_records import model_record, persist_model_bundle, source_evidence
from .outcome_data import checked_bytes, write_json
from .storage_proof import require


ROOT = "https://storage.googleapis.com/fao-gismgr-gaez-v5-data/DATA/GAEZ-V5/"
CATALOGUE = ("https://data.apps.fao.org/catalog/dataset/514c92d5-9e01-4c70-814a-80ea1ca9fe6a/"
             "resource/768b08ad-be9c-427a-84be-3a3d6dd7835a/download/_readme_res05.xlsx")
BOUNDARY = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM0/"
GRID = {"crs": "EPSG:4326", "width": 4320, "height": 2160,
        "transform": [1 / 12, 0, -180, 0, -1 / 12, 90]}


def catalogue_selection(asset, spec):
    checked_bytes(asset)
    with Path(asset["raw_path"]).open("rb") as stream:
        book = load_workbook(stream, read_only=True, data_only=True)
        try:
            crops = {str(row[0]): {"name": row[1], "group": str(row[2]).strip()}
                     for row in book["CODES_CROP"].iter_rows(min_row=2, values_only=True) if row[0]}
            periods = {str(row[0]): row[1] for row in book["CODES_PERIOD"].iter_rows(min_row=2, values_only=True) if row[0]}
            systems = {str(row[0]): row[1] for row in book["CODES_WATER_INPUT"].iter_rows(min_row=2, values_only=True) if row[0]}
            require(set(spec["crops"]) <= crops.keys() and set(spec["inputs"]) <= systems.keys(),
                    "Unknown GAEZ crop or production system")
            for period, bounds in spec["periods"].items():
                require(period.startswith("HP") and periods.get(period) == f"{bounds[0]}-{bounds[1]}",
                        "GAEZ historical period does not match its source definition")
            iterator = book["LIST_FILES"].values
            header = next(iterator)
            selected = []
            for values in iterator:
                row = dict(zip(header, values))
                if (row["MAPSET_CODE"] == "RES05-SXX" and row["PERIOD"] in spec["periods"]
                        and row["CROP"] in spec["crops"] and row["INPUT"] in spec["inputs"]
                        and row["CLIMATE_DATA_SOURCE"] == "AGERA5" and row["SSP"] == "HIST"):
                    selected.append(row)
            require({row["CROP"] for row in selected} == set(spec["crops"]), "A selected crop has no comparable source product")
            require(len({row["FILE_NAME"] for row in selected}) == len(selected), "Duplicate GAEZ catalogue products")
            return selected, {code: crops[code] for code in spec["crops"]}, systems
        finally:
            book.close()


def acquire_gaez(contract_path, output, resume=False):
    spec = yaml.safe_load(Path(contract_path).read_bytes())["gaez"]
    require(spec["climate_variables"] and all(code.startswith("RES01-") for code in spec["climate_variables"]),
            "Only crop-independent climate inputs belong in this reference cohort")
    output = Path(output)
    if resume:
        corpus = json.loads((output / "corpus.json").read_bytes())
        require(corpus["specification"] == spec, "A resumed acquisition cannot change its selection")
        require(corpus["kind"] == "gaez_reference_corpus", "Wrong acquisition corpus")
    else:
        output.mkdir(parents=True, exist_ok=False)
        corpus = {"schema_version": "1", "kind": "gaez_reference_corpus", "specification": spec,
                  "assets": [], "status": "in_progress"}
    cache = {asset["requested_url"]: asset for asset in corpus["assets"]}
    try:
        with system_trust_session() as session:
            def acquire(url):
                if url in cache:
                    checked_bytes(cache[url])
                    return cache[url]
                corpus["active_url"] = url
                write_json(output / "corpus.json", corpus)
                if url.endswith(".tif"):
                    response = session.head(url, timeout=60)
                    response.raise_for_status()
                    require(0 < int(response.headers["Content-Length"]) <= spec["maximum_asset_bytes"],
                            "Raster exceeds the declared acquisition budget")
                asset = archive_response(url, output / "raw", session=session, timeout=180)
                if url.endswith(".tif"):
                    require(asset["byte_count"] <= spec["maximum_asset_bytes"], "Downloaded raster exceeded its budget")
                cache[url] = asset
                corpus["assets"].append(asset)
                write_json(output / "corpus.json", corpus)
                return asset

            corpus["catalogue"] = acquire(CATALOGUE)
            products, corpus["crops"], corpus["systems"] = catalogue_selection(corpus["catalogue"], spec)
            corpus["boundary_metadata"] = acquire(BOUNDARY)
            boundary = json.loads(checked_bytes(corpus["boundary_metadata"]))
            require(boundary["boundaryISO"] == "IND" and boundary["boundaryType"] == "ADM0", "Wrong reference boundary")
            require(boundary["gjDownloadURL"].startswith("https://github.com/wmgeolab/geoBoundaries/raw/"),
                    "Unexpected boundary download origin")
            corpus["boundary"] = acquire(boundary["gjDownloadURL"])
            codes = ["RES05-SXX", *spec["climate_variables"]]
            corpus["definitions"] = {code: acquire(ROOT + f"MAPSET/{code}/GAEZ-V5.{code}.json") for code in codes}
            corpus["climate"] = {}
            for period in spec["periods"]:
                corpus["climate"][period] = {
                    code: acquire(ROOT + f"MAPSET/{code}/GAEZ-V5.{code}.{period}.AGERA5.HIST.tif")
                    for code in spec["climate_variables"]
                }
            corpus["static"] = {}
            for code in spec["static_variables"]:
                definition = acquire(ROOT + f"MAP/GAEZ-V5.{code}.json")
                metadata = json.loads(checked_bytes(definition))
                require(metadata["mapCode"] == code and metadata["downloadUrl"].startswith(ROOT + "MAP/"),
                        "Wrong static reference definition")
                corpus["static"][code] = {"definition": definition, "raster": acquire(metadata["downloadUrl"])}
            corpus["targets"] = []
            for product in products:
                filename = product["FILE_NAME"] + ".tif"
                url = ROOT + "MAPSET/RES05-SXX/" + quote(filename, safe="")
                corpus["targets"].append({"selection": product, "raster": acquire(url)})
        corpus["status"] = "complete"
        corpus.pop("error_type", None)
        corpus.pop("active_url", None)
        write_json(output / "corpus.json", corpus)
        return output / "corpus.json"
    except Exception as error:
        corpus.update(status="failed", error_type=type(error).__name__)
        write_json(output / "corpus.json", corpus)
        raise


def _metadata(asset, code):
    metadata = json.loads(checked_bytes(asset))
    require(metadata.get("code", metadata.get("mapCode")) in (code, "GAEZ-V5." + code),
            "Misbound provider variable definition")
    declared = metadata["srs"]
    require(declared.get("proj4") and rasterio.crs.CRS.from_string(declared["proj4"]).to_epsg() == 4326
            and metadata["measureUnit"], "Unsupported reference CRS/unit")
    require(declared.get("epsg") is None or str(declared["epsg"]) == "4326", "Conflicting source CRS declarations")
    return metadata


def reference_cells(corpus):
    boundary = json.loads(checked_bytes(corpus["boundary"]))
    require(boundary["type"] == "FeatureCollection" and boundary["features"], "Invalid India reference geometry")
    require(all(feature["properties"]["shapeGroup"] == "IND" for feature in boundary["features"]), "Non-Indian reference geometry")
    geometry = unary_union([shape(feature["geometry"]) for feature in boundary["features"]])
    require(geometry.is_valid, "Invalid reference boundary topology")
    inside = prep(geometry)
    transform = Affine(*GRID["transform"])
    step = corpus["specification"]["grid_stride"]
    require(isinstance(step, int) and step >= 1, "Invalid native-grid selection stride")
    west, south, east, north = geometry.bounds
    cells = []
    for row in range(0, GRID["height"], step):
        latitude = transform.f + transform.e * (row + 0.5)
        if not south <= latitude <= north:
            continue
        for column in range(0, GRID["width"], step):
            longitude = transform.c + transform.a * (column + 0.5)
            if west <= longitude <= east and inside.covers(Point(longitude, latitude)):
                identifier = "gaez5-cell-" + fingerprint([GRID, row, column])
                cells.append({"site_id": identifier, "row": row, "column": column,
                              "longitude": longitude, "latitude": latitude})
    require(cells, "No native reference cells within the selected Indian boundary")
    return cells


def validate_gaez_corpus(corpus):
    require(corpus["kind"] == "gaez_reference_corpus" and corpus["status"] == "complete", "GAEZ acquisition is incomplete")
    spec = corpus["specification"]
    products, crops, _ = catalogue_selection(corpus["catalogue"], spec)
    expected = {product["FILE_NAME"]: product for product in products}
    captured = {item["selection"]["FILE_NAME"]: item["selection"] for item in corpus["targets"]}
    require(expected == captured and len(captured) == len(corpus["targets"]), "Captured products differ from the source catalogue")
    require(set(corpus["climate"]) == set(spec["periods"]), "Missing or unexpected climate period")
    require(set(corpus["static"]) == set(spec["static_variables"]), "Missing or unexpected static reference")
    require(set(corpus["definitions"]) == {"RES05-SXX", *spec["climate_variables"]}, "Missing or unexpected variable definition")
    for period, variables in corpus["climate"].items():
        require(set(variables) == set(spec["climate_variables"]), "Missing climate variable")
        for code, asset in variables.items():
            require(asset["requested_url"] == ROOT + f"MAPSET/{code}/GAEZ-V5.{code}.{period}.AGERA5.HIST.tif",
                    "Climate variable or period is bound to the wrong source")
    for item in corpus["targets"]:
        product = item["selection"]
        expected_name = f"GAEZ-V5.RES05-SXX.{product['PERIOD']}.AGERA5.HIST.{product['CROP']}.{product['INPUT']}"
        require(product["FILE_NAME"] == expected_name and
                item["raster"]["requested_url"] == ROOT + "MAPSET/RES05-SXX/" + expected_name + ".tif",
                "Crop or production system is bound to the wrong target")
    for code, item in corpus["static"].items():
        definition = _metadata(item["definition"], code)
        require(item["raster"]["requested_url"] == definition["downloadUrl"], "Misbound static reference")
    return products, crops


def raster_values(asset, metadata, cells, categorical=False):
    checked_bytes(asset)
    with rasterio.open(asset["raw_path"]) as source:
        require(source.count == 1 and source.crs.to_epsg() == 4326, "Unsupported reference raster CRS/bands")
        require(all(expected is None or actual == expected for actual, expected in
                    zip((source.width, source.height), (metadata["width"], metadata["height"]))),
                "Raster/definition dimensions differ")
        require(np.allclose(tuple(source.transform)[:6], tuple(Affine.from_gdal(*metadata["affineTransform"]))[:6],
                            rtol=0, atol=1e-9), "Raster transform differs from source definition")
        factor = source.width // GRID["width"]
        require(factor >= 1 and source.width == GRID["width"] * factor and source.height == GRID["height"] * factor,
                "Reference raster does not nest exactly in the analysis grid")
        transform = source.transform
        coarse = [transform.a * factor, transform.b * factor, transform.c,
                  transform.d * factor, transform.e * factor, transform.f]
        require(np.allclose(coarse, GRID["transform"], rtol=0, atol=1e-9),
                "Reference pixel boundaries do not align")
        require(source.scales == (1.0,) and source.offsets == (0.0,), "Band-level scaling needs an explicit separate interpretation")
        top, left = min(c["row"] for c in cells) * factor, min(c["column"] for c in cells) * factor
        bottom, right = (max(c["row"] for c in cells) + 1) * factor, (max(c["column"] for c in cells) + 1) * factor
        data = source.read(1, window=Window(left, top, right - left, bottom - top), masked=True)
        values = []
        for cell in cells:
            y, x = cell["row"] * factor - top, cell["column"] * factor - left
            patch = data[y:y + factor, x:x + factor]
            valid = ~np.ma.getmaskarray(patch) & np.isfinite(patch.data)
            if metadata.get("noDataValue") is not None:
                valid &= patch.data != metadata["noDataValue"]
            if categorical:
                valid &= np.isin(patch.data, [int(key) for key in metadata["classes"]])
            else:
                require(not metadata.get("classes") and not metadata.get("flags"), "Unhandled categorical or flagged raster")
            bounds = 90 - (cell["row"] * factor + np.arange(factor + 1)) * source.res[1]
            weights = np.broadcast_to((np.sin(np.deg2rad(bounds[:-1])) - np.sin(np.deg2rad(bounds[1:])))[:, None], patch.shape)
            total, used = float(weights.sum()), float(weights[valid].sum())
            coverage = used / total
            if used == 0:
                values.append((None, 0.0))
            elif categorical:
                categories, inverse = np.unique(patch.data[valid], return_inverse=True)
                counts = np.bincount(inverse, weights=weights[valid])
                values.append((metadata["classes"][str(int(categories[np.argmax(counts)]))]["caption"], coverage))
            else:
                physical = patch.data[valid].astype("float64") * metadata["scale"] + metadata["offset"]
                value = float(physical[0]) if factor == 1 else float(np.average(physical, weights=weights[valid]))
                values.append((value, coverage))
        return values


def build_gaez(corpus_path, output, store):
    corpus = json.loads(Path(corpus_path).read_bytes())
    _, crops = validate_gaez_corpus(corpus)
    cells = reference_cells(corpus)
    metadata = {code: _metadata(asset, code) for code, asset in corpus["definitions"].items()}
    records, evidence = [], []

    def add(record, asset, locator, definition=None):
        records.append(record)
        evidence.append(source_evidence(record, asset, locator))
        if definition:
            evidence.append(source_evidence(record, definition, "provider:variable-definition", "definition"))

    boundary_definition = json.loads(checked_bytes(corpus["boundary_metadata"]))
    for cell in cells:
        values = {key: value for key, value in cell.items() if key != "site_id"}
        record = model_record("spatial_support", ["gaez5_grid", cell["site_id"]], {
            **values, "support_type": "native_grid_cell", "grid": GRID,
            "selection": "pixel_center_in_reference_boundary", "boundary_year": boundary_definition["boundaryYearRepresented"],
            "boundary_asset": corpus["boundary"]["raw_sha256"],
        }, cell["site_id"])
        add(record, corpus["boundary"], "FeatureCollection:geometry", corpus["boundary_metadata"])
    for code, crop in crops.items():
        record = model_record("crop_profile", ["gaez5", code], {
            "source_id": "gaez_v5", "source_crop_id": code, "source_name": crop["name"],
            "crop_group": crop["group"], "evidence_type": "published_parameter",
            "indian_cultivation_observed": False, "taxonomy_scope": "source_crop_or_crop_use",
        })
        add(record, corpus["catalogue"], f"CODES_CROP:{code}")
    for code, item in corpus["static"].items():
        definition = _metadata(item["definition"], code)
        categorical = bool(definition.get("classes"))
        for cell, (value, coverage) in zip(cells, raster_values(item["raster"], definition, cells, categorical)):
            record = model_record("environment_reference", ["gaez5", cell["site_id"], code], {
                "source_id": "gaez_v5", "metric_id": code, "value": None if categorical else value,
                "value_text": value if categorical else None, "value_type": "category" if categorical else "number",
                "unit": definition["measureUnit"],
                "temporal_support": "versioned_static_reference", "historical_measurement": False,
                "reference_definition": item["definition"]["raw_sha256"], "evidence_type": "modelled_product",
                "aggregation": "area_weighted_mode" if categorical else "area_weighted_mean",
                "valid_area_fraction": coverage, "availability": "missing" if value is None else
                "partial" if coverage < 1 - 1e-12 else "available",
            }, cell["site_id"])
            add(record, item["raster"], f"native-grid-cell:{cell['row']}:{cell['column']}", item["definition"])
    for period, variables in corpus["climate"].items():
        start, end = corpus["specification"]["periods"][period]
        for code, asset in variables.items():
            for cell, (value, coverage) in zip(cells, raster_values(asset, metadata[code], cells)):
                record = model_record("climate_normal", ["gaez5", cell["site_id"], code, period, "AGERA5", "HIST"], {
                    "source_id": "gaez_v5", "metric_id": code, "value": value, "unit": metadata[code]["measureUnit"],
                    "period_id": period, "window_start": f"{start}-01-01", "window_end": f"{end}-12-31",
                    "temporal_support": "published_20year_climate_normal", "climate_source": "AGERA5", "scenario": "HIST",
                    "valid_area_fraction": coverage, "evidence_type": "modelled_product",
                    "availability": "missing" if value is None else "available",
                }, cell["site_id"])
                add(record, asset, f"band:1:row:{cell['row']}:column:{cell['column']}", corpus["definitions"][code])
    coverage_counts = Counter()
    for item in corpus["targets"]:
        product = item["selection"]
        period, crop, system = product["PERIOD"], product["CROP"], product["INPUT"]
        start, end = corpus["specification"]["periods"][period]
        for cell, (value, coverage) in zip(cells, raster_values(item["raster"], metadata["RES05-SXX"], cells)):
            if value is None:
                coverage_counts["missing_source_target"] += 1
                continue
            require(0 <= value <= 10000 and coverage >= 1 - 1e-12, "Invalid source suitability index/support")
            record = model_record("crop_suitability", ["gaez5", cell["site_id"], crop, system, period, "AGERA5", "HIST"], {
                "source_id": "gaez_v5", "source_crop_id": crop, "crop_name": crops[crop]["name"],
                "crop_group": crops[crop]["group"], "production_system": system, "period_id": period,
                "window_start": f"{start}-01-01", "window_end": f"{end}-12-31", "climate_source": "AGERA5",
                "scenario": "HIST", "value": value, "unit": "Index", "metric_id": "RES05-SXX",
                "evidence_type": "modelled_product", "temporal_support": "published_20year_climate_normal",
                "target_basis": "all_land_reference_suitability_not_observed_crop_success",
            }, cell["site_id"])
            add(record, item["raster"], f"band:1:row:{cell['row']}:column:{cell['column']}", corpus["definitions"]["RES05-SXX"])
            coverage_counts["available_target"] += 1
    return persist_model_bundle(store, output, "india_gaez_reference_dataset", {
        "schema_version": "1", "task": "published_reference_suitability", "grid": GRID,
        "periods": corpus["specification"]["periods"], "coverage": dict(coverage_counts),
        "observed_crop_outcomes": False, "preplant_forecast": False, "current_field_soil_test": False,
        "climate_variables": corpus["specification"]["climate_variables"], "static_variables": corpus["specification"]["static_variables"],
        "source_licence": "CC-BY-4.0", "attribution": "FAO and IIASA, GAEZ v5 (2025).",
        "boundary_licence": boundary_definition["boundaryLicense"], "boundary_year": boundary_definition["boundaryYearRepresented"],
        "crop_dates_or_perennial_age_available": False,
    }, corpus, records, evidence)
