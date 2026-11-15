from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import tempfile
from xml.etree import ElementTree as XML
import zipfile

from defusedxml import ElementTree as SafeXML
from defusedxml.common import DefusedXmlException

from agri_data.contracts.geography import KML, _documents, parse_boundaries
from .errors import WorkspaceError
from .geometry import prepare_geometry


MEDIA_TYPES = {"geojson": "application/geo+json", "kml": "application/vnd.google-earth.kml+xml",
               "kmz": "application/vnd.google-earth.kmz"}


def parse_upload(content, filename, project_id, namespace):
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".geojson":
            document = json.loads(content)
            if document.get("type") != "FeatureCollection" or not isinstance(document.get("features"), list):
                raise ValueError("GeoJSON imports require a FeatureCollection")
            if not 1 <= len(document["features"]) <= 100:
                raise ValueError("Import between 1 and 100 features")
            candidates, rejected, identifiers = [], [], set()
            for index, feature in enumerate(document["features"]):
                locator = f"features[{index}]"
                try:
                    if not isinstance(feature, dict) or feature.get("type") != "Feature":
                        raise ValueError("Expected a GeoJSON Feature")
                    prepared = prepare_geometry(feature.get("geometry"))
                    properties = feature.get("properties") or {}
                    if not isinstance(properties, dict):
                        raise ValueError("Feature properties must be an object")
                    identifier = feature.get("id")
                    if identifier is None:
                        identifier = properties.get("source_identifier") or sha256(
                            json.dumps(feature["geometry"], sort_keys=True).encode()).hexdigest()
                    if not isinstance(identifier, (str, int)) or isinstance(identifier, bool):
                        raise ValueError("Feature IDs must be strings or integers")
                    identifier = str(identifier)
                    if identifier in identifiers:
                        raise ValueError("Duplicate source identifier")
                    identifiers.add(identifier)
                    candidates.append({**prepared, "source_identifier": identifier, "locator": locator,
                                       "metadata": properties, "name": properties.get("name")})
                except (ValueError, TypeError) as error:
                    rejected.append({"locator": locator, "reason": str(error)})
            return candidates, rejected
        if suffix not in (".kml", ".kmz"):
            raise ValueError("Upload a .kml, .kmz, or .geojson file")
        if suffix == ".kmz":
            with zipfile.ZipFile(BytesIO(content)) as archive:
                entries = archive.infolist()
                if len(entries) > 256 or len({entry.filename.casefold() for entry in entries}) != len(entries):
                    raise ValueError("KMZ has too many or duplicate archive members")
                for entry in entries:
                    name = entry.filename.replace("\\", "/")
                    if name.startswith("/") or ".." in PurePosixPath(name).parts or ":" in name:
                        raise ValueError("Unsafe KMZ member path")
                    if entry.flag_bits & 1 or entry.file_size > max(1, entry.compress_size) * 200:
                        raise ValueError("Encrypted or excessively compressed KMZ members are unsupported")
        placemarks, positions = 0, 0
        for _, content_xml in _documents(content, suffix):
            root = SafeXML.fromstring(content_xml, forbid_dtd=True)
            stack = [(root, 0)]
            while stack:
                element, depth = stack.pop()
                if depth > 64:
                    raise ValueError("KML nesting limit exceeded")
                if element.tag == KML + "Placemark":
                    placemarks += 1
                if element.tag == KML + "coordinates":
                    positions += len((element.text or "").split())
                if placemarks > 100 or positions > 100000:
                    raise ValueError("KML exceeds 100 placemarks or 100000 total positions")
                stack.extend((child, depth + 1) for child in element)
        with tempfile.TemporaryDirectory(prefix="agri-preview-") as temporary:
            path = Path(temporary) / ("upload" + suffix)
            path.write_bytes(content)
            records, rejected = parse_boundaries(path, project_id, namespace)
        candidates = []
        for record in records:
            try:
                prepared = prepare_geometry(json.loads(json.dumps(record.record()["original_geometry"])))
                candidates.append({**prepared, "source_identifier": record.source_identifier,
                    "locator": record.locator, "metadata": record.metadata, "name": record.metadata.get("name")})
            except ValueError as error:
                rejected.append({"locator": record.locator, "reason": str(error)})
        return candidates, rejected
    except (ValueError, TypeError, AttributeError, zipfile.BadZipFile, DefusedXmlException, XML.ParseError):
        raise WorkspaceError(422, "invalid_import", "Invalid or unsafe boundary document; no fields were changed") from None


def serialize_export(features, format_name):
    if format_name == "geojson":
        return json.dumps({"type": "FeatureCollection", "features": features},
                          ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
    XML.register_namespace("", KML[1:-1])
    root = XML.Element(KML + "kml")
    document = XML.SubElement(root, KML + "Document")
    for feature in features:
        properties = feature["properties"]
        parent = document
        source = properties.get("source_metadata", {})
        for folder in source.get("folders", []) if isinstance(source.get("folders", []), list) else []:
            parent = XML.SubElement(parent, KML + "Folder")
            XML.SubElement(parent, KML + "name").text = str(folder)
        placemark = XML.SubElement(parent, KML + "Placemark", id="field-" + sha256(feature["id"].encode()).hexdigest()[:24])
        XML.SubElement(placemark, KML + "name").text = properties.get("name") or feature["id"]
        extended = XML.SubElement(placemark, KML + "ExtendedData")
        for key, value in properties.items():
            item = XML.SubElement(extended, KML + "Data", name=key)
            XML.SubElement(item, KML + "value").text = json.dumps(value, ensure_ascii=False, allow_nan=False)
        geometry = feature["geometry"]
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        owner = placemark if geometry["type"] == "Polygon" else XML.SubElement(placemark, KML + "MultiGeometry")
        for rings in polygons:
            polygon = XML.SubElement(owner, KML + "Polygon")
            for index, ring in enumerate(rings):
                boundary = XML.SubElement(polygon, KML + ("outerBoundaryIs" if index == 0 else "innerBoundaryIs"))
                linear = XML.SubElement(boundary, KML + "LinearRing")
                XML.SubElement(linear, KML + "coordinates").text = " ".join(
                    ",".join(format(number, ".17g") for number in position) for position in ring)
    content = XML.tostring(root, encoding="utf-8", xml_declaration=True)
    if format_name == "kml":
        return content
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("doc.kml", content)
    return output.getvalue()
