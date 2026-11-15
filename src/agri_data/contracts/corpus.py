"""Acquire a bounded public agricultural reference corpus without invented fields.

The Dutch reference parcel verifies infrastructure only. It is not evidence for
Indian crop parameters, a cultivar, a farmer's sowing date, or any device category.
"""

from hashlib import sha256
from pathlib import Path
import json
import xml.etree.ElementTree as ET

from shapely.geometry import shape

from .assets import archive_response


PARCEL_ID = "364716d2-7384-5941-8ad5-37952c10d6e1"
COLLECTION = "https://api.pdok.nl/rvo/gewaspercelen/ogc/v1/collections/brpgewas"


def acquire_reference_corpus(destination: Path) -> dict:
    """Preserve original GeoJSON, deterministically translate its real rings to KML."""
    raw = destination / "raw"
    metadata = archive_response(COLLECTION, raw, {"f": "json"})
    parcel_asset = archive_response(f"{COLLECTION}/items/{PARCEL_ID}", raw, {"f": "json"})
    parcel = json.loads(Path(parcel_asset["raw_path"]).read_bytes())
    if parcel.get("id") != PARCEL_ID or parcel.get("type") != "Feature":
        raise ValueError("Provider returned a different parcel or unexpected schema")
    geometry = shape(parcel["geometry"])
    if geometry.geom_type not in ("Polygon", "MultiPolygon") or not geometry.is_valid:
        raise ValueError("Authentic parcel is not a valid polygon; do not replace it")
    properties = parcel["properties"]
    namespace = "http://www.opengis.net/kml/2.2"
    ET.register_namespace("", namespace)
    def node(parent, tag, text=None, **attributes):
        element = ET.SubElement(parent, f"{{{namespace}}}{tag}", attributes)
        element.text = text
        return element
    root = ET.Element(f"{{{namespace}}}kml")
    document = node(root, "Document")
    placemark = node(document, "Placemark", id=PARCEL_ID)
    node(placemark, "name", PARCEL_ID)
    extended = node(placemark, "ExtendedData")
    for key, value in properties.items():
        item = node(extended, "Data", name=key)
        node(item, "value", str(value))
    polygons = [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)
    parent = placemark if len(polygons) == 1 else node(placemark, "MultiGeometry")
    for polygon in polygons:
        element = node(parent, "Polygon")
        rings = [("outerBoundaryIs", polygon.exterior)] + [
            ("innerBoundaryIs", ring) for ring in polygon.interiors
        ]
        for boundary, ring in rings:
            coordinates = " ".join(",".join(str(v) for v in point) for point in ring.coords)
            node(node(node(element, boundary), "LinearRing"), "coordinates", coordinates)
    kml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    kml_path = destination / f"{sha256(kml_bytes).hexdigest()}.kml"
    if kml_path.exists():
        if kml_path.read_bytes() != kml_bytes:
            raise ValueError("Existing KML translation does not match its hash")
    else:
        kml_path.write_bytes(kml_bytes)
    representative = geometry.representative_point()
    year = int(properties["jaar"])
    weather_asset = archive_response(
        "https://power.larc.nasa.gov/api/temporal/daily/point",
        raw,
        {
            "longitude": representative.x, "latitude": representative.y,
            "start": f"{year}0101", "end": f"{year}1231",
            "parameters": "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN",
            "community": "AG", "format": "JSON",
        },
    )
    manifest = {
        "schema_version": "1", "scope": "public infrastructure reference corpus",
        "boundary_source": "Rijksdienst voor Ondernemend Nederland / PDOK BRP Gewaspercelen",
        "collection_metadata": metadata, "parcel_asset": parcel_asset,
        "parcel_id": PARCEL_ID, "provider_properties": properties,
        "kml_path": str(kml_path.resolve()), "kml_sha256": sha256(kml_bytes).hexdigest(),
        "translation": "GeoJSON polygon rings to KML longitude/latitude; no altered coordinates or generated boundaries",
        "weather_asset": weather_asset,
        "acceptance_limitations": [
            "Crop code/name and year are provider declarations, not independently verified field observations.",
            "No cultivar, sowing/harvest date, sensor or laboratory measurements were supplied.",
            "This reference does not replace a regional crop/rotation acceptance corpus.",
            "No scientific or database acceptance gate is certified by acquisition alone.",
        ],
    }
    path = destination / f"{weather_asset['request_id']}.corpus.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"manifest": str(path.resolve()), **manifest}
