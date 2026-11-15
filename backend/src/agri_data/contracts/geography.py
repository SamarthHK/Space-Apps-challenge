"""Boundary ingestion without generated fields, implicit repairs or remote links."""

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import math
import zipfile

from defusedxml import ElementTree as ET
import numpy as np
from pyproj import CRS, Transformer
from shapely import force_2d, make_valid, normalize, transform
from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.validation import explain_validity

from .identity import stable_field_id


KML = "{http://www.opengis.net/kml/2.2}"
MAX_XML_BYTES = 32 * 1024 * 1024


@dataclass
class Boundary:
    field_id: str
    source_identifier: str
    locator: str
    metadata: dict
    original: Polygon | MultiPolygon
    geometry: Polygon | MultiPolygon
    repair_notes: str | None
    metric_crs: str
    area_m2: float
    perimeter_m: float

    def record(self):
        return {
            "field_id": self.field_id, "source_identifier": self.source_identifier,
            "source_record_locator": self.locator, "metadata": self.metadata,
            "original_geometry": mapping(self.original), "geometry": mapping(self.geometry),
            "repair_notes": self.repair_notes, "metric_crs": self.metric_crs,
            "area_m2": self.area_m2, "area_ha": self.area_m2 / 10000,
            "perimeter_m": self.perimeter_m, "bounds": list(self.geometry.bounds),
            "representative_point": mapping(self.geometry.representative_point()),
        }


def metric_geometry(geometry):
    west, south, east, north = geometry.bounds
    if east - west > 180:
        raise ValueError("Antimeridian-spanning geometry requires explicit longitude unwrapping")
    point = geometry.representative_point()
    if -80 <= south and north <= 84:
        zone = max(1, min(60, math.floor((point.x + 180) / 6) + 1))
        crs = CRS.from_epsg((32600 if point.y >= 0 else 32700) + zone)
    else:
        raise ValueError("Polar geometry requires a reviewed metric projection")
    transformer = Transformer.from_crs(4326, crs, always_xy=True)
    return crs, transform(force_2d(geometry), lambda coordinates: np.column_stack(
        transformer.transform(coordinates[:, 0], coordinates[:, 1])
    ))


def _documents(payload, suffix):
    if suffix == ".kml":
        if len(payload) > MAX_XML_BYTES:
            raise ValueError("KML exceeds the configured XML size limit")
        return [("document", payload)]
    if suffix != ".kmz":
        raise ValueError("Expected an actual .kml or .kmz file")
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        members = [item for item in archive.infolist() if item.filename.lower().endswith(".kml")]
        if not members:
            raise ValueError("KMZ contains no KML document")
        if len({item.filename for item in members}) != len(members):
            raise ValueError("KMZ contains ambiguous duplicate document names")
        if sum(item.file_size for item in members) > MAX_XML_BYTES:
            raise ValueError("KMZ exceeds the configured uncompressed XML size limit")
        # Read members in memory; never extract paths or follow NetworkLinks.
        return [(item.filename, archive.read(item)) for item in members]


def _ring(polygon, tag):
    boundaries = polygon.findall(KML + tag)
    result = []
    for boundary in boundaries:
        coordinates = boundary.find(f"{KML}LinearRing/{KML}coordinates")
        if coordinates is None or not coordinates.text:
            raise ValueError("Polygon boundary has no recorded coordinates")
        points = []
        for text in coordinates.text.split():
            point = tuple(float(value) for value in text.split(","))
            if len(point) not in (2, 3) or not all(math.isfinite(value) for value in point):
                raise ValueError("Invalid coordinate dimensions or nonfinite ordinate")
            if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                raise ValueError("KML longitude/latitude is outside EPSG:4326 bounds")
            points.append(point)
        if len(points) < 4 or points[0] != points[-1]:
            raise ValueError("LinearRing is not explicitly closed with at least four coordinates")
        if len({len(point) for point in points}) != 1:
            raise ValueError("Mixed coordinate dimensions in LinearRing")
        result.append(points)
    return result


def _placemarks(element, parents=()):
    tag = element.tag.removeprefix(KML)
    if tag in ("Folder", "Document"):
        name = element.findtext(KML + "name")
        if name:
            parents = (*parents, name)
    if tag == "Placemark":
        yield element, parents
    else:
        for child in element:
            yield from _placemarks(child, parents)


def parse_boundaries(path: Path, project_id: str, source_namespace: str, *, allow_repair=False,
                     repair_reference=None, repair_area_tolerance_m2=None, repair_shape_tolerance_m2=None):
    if not project_id.strip() or not source_namespace.strip():
        raise ValueError("Project and source namespace must be explicitly supplied")
    payload = path.read_bytes()
    records, rejected, identities = [], [], set()
    references = {}
    if allow_repair:
        if repair_reference is None or repair_area_tolerance_m2 is None or repair_shape_tolerance_m2 is None:
            raise ValueError("Repair requires an authentic reviewed reference and predeclared area/shape tolerances")
        if (not math.isfinite(repair_area_tolerance_m2) or repair_area_tolerance_m2 < 0
                or not math.isfinite(repair_shape_tolerance_m2) or repair_shape_tolerance_m2 < 0):
            raise ValueError("Repair tolerances must be finite and nonnegative")
        reference_fields, reference_rejected = parse_boundaries(repair_reference, project_id, source_namespace)
        if reference_rejected:
            raise ValueError("Repair reference contains invalid or unsupported boundaries")
        references = {field.source_identifier: field.geometry for field in reference_fields}
    for document_name, xml in _documents(payload, path.suffix.lower()):
        document = ET.fromstring(xml, forbid_dtd=True)
        if document.tag != KML + "kml":
            raise ValueError("Expected a KML 2.2 document with its declared namespace")
        for index, (placemark, folders) in enumerate(_placemarks(document)):
            locator = f"{document_name}/Placemark[{index + 1}]"
            try:
                forbidden = ("Point", "LineString", "Model", "Track")
                if any(node.tag.rsplit("}", 1)[-1] in forbidden for node in placemark.iter()):
                    raise ValueError("Placemark contains unsupported non-polygon geometry")
                polygons = []
                for polygon in placemark.iter(KML + "Polygon"):
                    outer = _ring(polygon, "outerBoundaryIs")
                    holes = _ring(polygon, "innerBoundaryIs")
                    if len(outer) != 1:
                        raise ValueError("Polygon needs exactly one outer boundary")
                    polygons.append(Polygon(outer[0], holes))
                if not polygons:
                    raise ValueError("Placemark has no polygon geometry")
                original = polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)
                geometry = force_2d(original)
                repair = None
                if geometry.is_empty:
                    raise ValueError("Empty agricultural boundary")
                if not geometry.is_valid:
                    reason = explain_validity(geometry)
                    if not allow_repair:
                        raise ValueError(f"Invalid geometry; explicit repair approval required: {reason}")
                    geometry = make_valid(geometry)
                    if geometry.geom_type not in ("Polygon", "MultiPolygon") or not geometry.is_valid:
                        raise ValueError("Repair did not produce exclusively valid polygon geometry")
                    provider_id = placemark.get("id")
                    if not provider_id or provider_id not in references:
                        raise ValueError("Repair reference must match an explicit original provider placemark ID")
                    crs, candidate = metric_geometry(geometry)
                    transform_reference = Transformer.from_crs(4326, crs, always_xy=True)
                    reference = transform(force_2d(references[provider_id]), lambda coords: np.column_stack(
                        transform_reference.transform(coords[:, 0], coords[:, 1])))
                    if (abs(candidate.area - reference.area) > repair_area_tolerance_m2
                            or candidate.symmetric_difference(reference).area > repair_shape_tolerance_m2):
                        raise ValueError("Repair exceeds predeclared reference area/shape tolerances")
                    repair = f"GEOS make_valid: {reason}; original coordinates retained separately"
                name = placemark.findtext(KML + "name")
                identifier = placemark.get("id") or json.dumps(
                    [*folders, name] if name else ["geometry_sha256", sha256(normalize(geometry).wkb).hexdigest()],
                    ensure_ascii=True, separators=(",", ":"),
                )
                field_id = stable_field_id(project_id, source_namespace, identifier)
                if field_id in identities:
                    raise ValueError("Duplicate field identity in input; disambiguate original source identifiers")
                crs, metric = metric_geometry(geometry)
                extended = [
                    {"name": item.get("name"), "value": item.findtext(KML + "value")}
                    for item in placemark.findall(f"{KML}ExtendedData/{KML}Data")
                ]
                schema_values = [
                    {"schema_url": schema.get("schemaUrl"), "name": item.get("name"), "value": item.text}
                    for schema in placemark.findall(f"{KML}ExtendedData/{KML}SchemaData")
                    for item in schema.findall(KML + "SimpleData")
                ]
                records.append(Boundary(
                    field_id, identifier, locator,
                    {"name": name, "folders": list(folders), "extended_data": extended,
                     "schema_data": schema_values, "source_namespace": source_namespace,
                     "description": placemark.findtext(KML + "description"),
                     "has_altitude": bool(original.has_z),
                     "repair_validation": ({
                         "reference_sha256": sha256(repair_reference.read_bytes()).hexdigest(),
                         "area_tolerance_m2": repair_area_tolerance_m2,
                         "shape_tolerance_m2": repair_shape_tolerance_m2,
                     } if repair else None),
                     "analysis_dimensions": "2D footprint; original altitude retained in original geometry"},
                    original, geometry, repair, crs.to_string(), metric.area, metric.length,
                ))
                identities.add(field_id)
            except (ValueError, TypeError) as error:
                rejected.append({"locator": locator, "reason": str(error)})
        for link in document.iter(KML + "NetworkLink"):
            rejected.append({"locator": document_name + "/NetworkLink", "reason": "Remote links are not followed"})
    if not records and not rejected:
        rejected.append({"locator": "document", "reason": "No agricultural placemarks found"})
    return records, rejected
