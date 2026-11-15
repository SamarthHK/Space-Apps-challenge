"""
KML / KMZ Ingestion and Parsing Module.
Extracts placemark polygons, metadata, extended attributes, and generates stable field IDs.
"""

from pathlib import Path
from typing import Union, List, Dict, Any, Optional
import zipfile
import defusedxml.ElementTree as ET
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.validation import make_valid
import json

KML_NS = "{http://www.opengis.net/kml/2.2}"


def _parse_coordinates(coord_str: str) -> List[tuple]:
    """Parse KML coordinate tuple string: lon,lat,alt lon,lat,alt ..."""
    coords = []
    for chunk in coord_str.strip().split():
        parts = chunk.split(",")
        if len(parts) >= 2:
            try:
                lon = float(parts[0])
                lat = float(parts[1])
                coords.append((lon, lat))
            except ValueError:
                continue
    return coords


def _extract_placemark_geometry(elem: ET.Element) -> Optional[Union[Polygon, MultiPolygon]]:
    """Recursively extract Polygon or MultiPolygon from KML Placemark element."""
    polygon_elem = elem.find(f".//{KML_NS}Polygon")
    if polygon_elem is not None:
        outer_coords_elem = polygon_elem.find(f".//{KML_NS}outerBoundaryIs//{KML_NS}coordinates")
        if outer_coords_elem is not None and outer_coords_elem.text:
            outer_ring = _parse_coordinates(outer_coords_elem.text)
            if len(outer_ring) < 3:
                return None
            # Check for inner boundaries (holes)
            inner_rings = []
            for inner_elem in polygon_elem.findall(f".//{KML_NS}innerBoundaryIs//{KML_NS}coordinates"):
                if inner_elem.text:
                    ring = _parse_coordinates(inner_elem.text)
                    if len(ring) >= 3:
                        inner_rings.append(ring)
            return Polygon(outer_ring, inner_rings)

    # Check for MultiGeometry with Polygons
    mg_elem = elem.find(f".//{KML_NS}MultiGeometry")
    if mg_elem is not None:
        poly_list = []
        for poly_child in mg_elem.findall(f".//{KML_NS}Polygon"):
            outer_coords_elem = poly_child.find(f".//{KML_NS}outerBoundaryIs//{KML_NS}coordinates")
            if outer_coords_elem is not None and outer_coords_elem.text:
                outer_ring = _parse_coordinates(outer_coords_elem.text)
                if len(outer_ring) >= 3:
                    poly_list.append(Polygon(outer_ring))
        if poly_list:
            return MultiPolygon(poly_list)

    return None


def _extract_extended_data(elem: ET.Element) -> Dict[str, Any]:
    """Extract ExtendedData key-values from Placemark element."""
    data = {}
    ext_data = elem.find(f"{KML_NS}ExtendedData")
    if ext_data is not None:
        # SchemaData
        for data_elem in ext_data.findall(f"{KML_NS}Data"):
            name = data_elem.attrib.get("name")
            val_elem = data_elem.find(f"{KML_NS}value")
            if name and val_elem is not None and val_elem.text:
                data[name] = val_elem.text.strip()
    return data


def parse_kml_or_kmz(file_path: Union[str, Path]) -> gpd.GeoDataFrame:
    """
    Parses a KML or KMZ file, extracts all polygon placemarks,
    cleans & repairs geometries, and assigns stable field identifiers.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"KML/KMZ file not found: {path}")

    # Handle KMZ by extracting doc.kml
    kml_content: bytes
    if path.suffix.lower() == ".kmz":
        with zipfile.ZipFile(path, "r") as z:
            kml_files = [n for n in z.namelist() if n.endswith(".kml")]
            if not kml_files:
                raise ValueError(f"No .kml found inside KMZ: {path}")
            kml_content = z.read(kml_files[0])
    else:
        with open(path, "rb") as f:
            kml_content = f.read()

    root = ET.fromstring(kml_content)

    records = []
    # Search folders or direct document placemarks
    for placemark in root.findall(f".//{KML_NS}Placemark"):
        geom = _extract_placemark_geometry(placemark)
        if geom is None:
            continue

        # Validate and repair
        if not geom.is_valid:
            geom = make_valid(geom)
            if not isinstance(geom, (Polygon, MultiPolygon)):
                continue

        name_elem = placemark.find(f"{KML_NS}name")
        name = name_elem.text.strip() if name_elem is not None and name_elem.text else "Unnamed Plot"

        desc_elem = placemark.find(f"{KML_NS}description")
        desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""

        # Parent folder name if available
        parent_folder = "Default"
        parent = placemark.find("..")
        if parent is not None and parent.tag == f"{KML_NS}Folder":
            fname = parent.find(f"{KML_NS}name")
            if fname is not None and fname.text:
                parent_folder = fname.text.strip()

        ext_data = _extract_extended_data(placemark)

        records.append({
            "name": name,
            "description": desc,
            "folder": parent_folder,
            "extended_data": json.dumps(ext_data) if ext_data else None,
            "geometry": geom
        })

    if not records:
        raise ValueError(f"No valid polygon geometries found in KML: {path}")

    gdf = gpd.GeoDataFrame(records, crs="EPSG:4326")
    gdf["field_id"] = [f"FIELD_{i:04d}" for i in range(1, len(gdf) + 1)]

    # Reorder columns with field_id first
    cols = ["field_id", "name", "description", "folder", "extended_data", "geometry"]
    return gdf[cols]


def load_kml(file_path: Union[str, Path]) -> gpd.GeoDataFrame:
    """Convenience wrapper for parse_kml_or_kmz."""
    return parse_kml_or_kmz(file_path)
