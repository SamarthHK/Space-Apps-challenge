export const KML_MEDIA_TYPE = 'application/vnd.google-earth.kml+xml';

function xmlText(value) {
  if (typeof value !== 'string' || /[\u0000-\u0008\u000B\u000C\u000E-\u001F\uD800-\uDFFF\uFFFE\uFFFF]/u.test(value)) {
    throw new Error('KML text contains characters that XML cannot represent.');
  }
  const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' };
  return value.replace(/[&<>"']/g, character => entities[character]);
}

export function boundaryKml(geometry, { name = null, id } = {}) {
  if (typeof id !== 'string' || !/^[A-Za-z_][A-Za-z0-9_.-]*$/.test(id)) {
    throw new Error('Supply a stable XML-compatible drawing identifier.');
  }
  if (!['Polygon', 'MultiPolygon'].includes(geometry?.type)) {
    throw new Error('Supply a Polygon or MultiPolygon geometry.');
  }
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates;
  if (!Array.isArray(polygons) || !polygons.length) throw new Error('The boundary has no polygons.');
  let dimensions;
  let positions = 0;
  const serialized = [];
  for (const rings of polygons) {
    if (!Array.isArray(rings) || !rings.length) throw new Error('Each polygon needs an outer ring.');
    const boundaries = [];
    for (const [index, ring] of rings.entries()) {
      if (!Array.isArray(ring) || ring.length < 4) throw new Error('Each ring needs at least four closed positions.');
      const coordinates = [];
      for (const position of ring) {
        if (!Array.isArray(position) || ![2, 3].includes(position.length)) {
          throw new Error('Positions must contain longitude, latitude and optional altitude.');
        }
        dimensions ??= position.length;
        if (position.length !== dimensions) throw new Error('Use consistent coordinate dimensions throughout the boundary.');
        for (const value of position) {
          if (!Number.isFinite(value)) throw new Error('Coordinates must be finite numbers.');
        }
        if (Math.abs(position[0]) > 180 || Math.abs(position[1]) > 90) {
          throw new Error('Longitude and latitude must be within -180 to 180 and -90 to 90.');
        }
        if (++positions > 10000) throw new Error('A boundary may contain at most 10000 positions.');
        coordinates.push(position.join(','));
      }
      if (!ring[0].every((value, axis) => value === ring.at(-1)[axis])) {
        throw new Error('Each ring must end at its exact starting position.');
      }
      const tag = index === 0 ? 'outerBoundaryIs' : 'innerBoundaryIs';
      boundaries.push(`<${tag}><LinearRing><coordinates>${coordinates.join(' ')}</coordinates></LinearRing></${tag}>`);
    }
    serialized.push(`<Polygon>${boundaries.join('')}</Polygon>`);
  }
  const shape = geometry.type === 'Polygon' ? serialized[0] : `<MultiGeometry>${serialized.join('')}</MultiGeometry>`;
  return '<?xml version="1.0" encoding="UTF-8"?>\n'
    + '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
    + `<Placemark id="${xmlText(id)}">${name === null ? '' : `<name>${xmlText(name)}</name>`}`
    + `${shape}</Placemark></Document></kml>\n`;
}
