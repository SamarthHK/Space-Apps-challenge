import { test } from 'node:test';
import assert from 'node:assert/strict';
import { boundaryKml } from '../src/api/kml.js';

const polygon = { type: 'Polygon', coordinates: [[[10, 10], [11, 10], [11, 11], [10, 10]]] };
const options = { id: 'drawn-stable-input' };
const ringsFrom = xml => [...xml.matchAll(/<coordinates>([^<]+)<\/coordinates>/g)]
  .map(match => match[1].split(' ').map(position => position.split(',').map(Number)));

test('KML preserves multipart boundaries, holes and supplied altitude without flattening coordinates', () => {
  const geometry = { type: 'MultiPolygon', coordinates: [
    [[[10, 10, 3], [14, 10, 4], [14, 14, 5], [10, 14, 6], [10, 10, 3]],
      [[11, 11, 3], [11, 12, 3], [12, 12, 3], [12, 11, 3], [11, 11, 3]]],
    [[[15, 10, -2], [16, 10, 3], [16, 11, 4], [15, 10, -2]]],
  ] };
  const xml = boundaryKml(geometry, options);
  assert.match(xml, /<kml xmlns="http:\/\/www.opengis.net\/kml\/2.2">/);
  assert.match(xml, /<MultiGeometry>/);
  assert.equal([...xml.matchAll(/<Polygon>/g)].length, 2);
  assert.equal([...xml.matchAll(/<innerBoundaryIs>/g)].length, 1);
  assert.deepEqual(ringsFrom(xml), geometry.coordinates.flat());
});

test('unnamed two-dimensional drawings do not gain invented names or zero altitude', () => {
  const xml = boundaryKml(polygon, options);
  assert.doesNotMatch(xml, /<name>|<MultiGeometry>/);
  assert.deepEqual(ringsFrom(xml), polygon.coordinates);
});

test('KML escapes labels, accepts valid Unicode and refuses unrepresentable XML text or identifiers', () => {
  const xml = boundaryKml(polygon, { ...options, name: 'R&D <"north"> \'plot\' \uD83C\uDF0D' });
  assert.match(xml, /<name>R&amp;D &lt;&quot;north&quot;&gt; &apos;plot&apos; \uD83C\uDF0D<\/name>/u);
  for (const name of ['bad\u0000', 'bad\u000B', 'bad\uD800', 'bad\uDC00', 'bad\uFFFE', 42]) {
    assert.throws(() => boundaryKml(polygon, { ...options, name }), /XML/);
  }
  assert.throws(() => boundaryKml(polygon, { id: 'plot" injected="true' }), /identifier/);
});

test('malformed, open, mixed-dimensional, out-of-range and oversized rings fail before upload', () => {
  const cases = [
    null, { type: 'Point', coordinates: [10, 10] }, { type: 'MultiPolygon', coordinates: [] },
    { type: 'Polygon', coordinates: [] },
    ...[
      [[10, 10], [11, 10], [10, 10]],
      [[10, 10], [11, 10], [11, 11], [10, 11]],
      [[10, 10], [11, 10, 0], [11, 11], [10, 10]],
      [[10, 10], [Infinity, 10], [11, 11], [10, 10]],
      [[10, 10], ['11', 10], [11, 11], [10, 10]],
      [[10, 10], [181, 10], [11, 11], [10, 10]],
      [[10, 10], [11, -91], [11, 11], [10, 10]],
      Array.from({ length: 10001 }, () => [10, 10]),
    ].map(ring => ({ type: 'Polygon', coordinates: [ring] })),
  ];
  for (const geometry of cases) assert.throws(() => boundaryKml(geometry, options));
});
