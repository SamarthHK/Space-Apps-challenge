import math

from shapely import force_2d
from shapely.geometry import mapping, shape

from agri_data.contracts.geography import metric_geometry


def prepare_geometry(value):
    if not isinstance(value, dict) or value.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError("Supply a Polygon or MultiPolygon in EPSG:4326 longitude/latitude")
    coordinates = value.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise ValueError("A nonempty polygon boundary is required")
    polygons = [coordinates] if value["type"] == "Polygon" else coordinates
    dimensions, count = set(), 0
    for polygon in polygons:
        if not isinstance(polygon, list) or not polygon:
            raise ValueError("A polygon needs an outer ring")
        for ring in polygon:
            if not isinstance(ring, list) or len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("Rings must be explicitly closed with at least four positions")
            for position in ring:
                count += 1
                if count > 10000:
                    raise ValueError("A field boundary may contain at most 10000 positions")
                if (not isinstance(position, list) or len(position) not in (2, 3)
                        or any(isinstance(number, bool) or not isinstance(number, (int, float))
                               or not math.isfinite(number) for number in position)):
                    raise ValueError("Coordinates must contain finite numeric ordinates")
                if not -180 <= position[0] <= 180 or not -90 <= position[1] <= 90:
                    raise ValueError("Coordinate is outside longitude/latitude bounds")
                dimensions.add(len(position))
    if len(dimensions) != 1:
        raise ValueError("Coordinate dimensions must be consistent")
    original = shape(value)
    geometry = force_2d(original)
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Invalid polygon; no implicit repair is performed")
    crs, metric = metric_geometry(geometry)
    if not math.isfinite(metric.area) or metric.area <= 0:
        raise ValueError("Boundary has no finite positive projected area")
    return {"geometry": mapping(geometry), "original_geometry": mapping(original),
            "metric_crs": crs.to_string(), "area_m2": metric.area, "perimeter_m": metric.length}
