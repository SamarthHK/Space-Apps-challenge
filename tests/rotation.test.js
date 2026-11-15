import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEMO_PARCEL, summarizeDemoGeometry, buildDemoExplanation } from '../src/data/rotationDemo.js';

const square = (x = 0, y = 0, size = 0.001) =>
  [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]];
const polygon = ring => ({ type: 'Polygon', coordinates: [ring] });

test('selected coordinates determine approximate hectares, location and boundary point count', () => {
  const summary = summarizeDemoGeometry(polygon(square()));
  assert.ok(Math.abs(summary.areaHa - 1.2364) < 0.001);
  assert.equal(summary.vertices, 4);
  assert.equal(summary.longitude, 0.0005);
  assert.equal(summary.latitude, 0.0005);
  assert.ok(summarizeDemoGeometry(DEMO_PARCEL).areaHa > 2);
  const larger = summarizeDemoGeometry(polygon(square(0, 0, 0.002)));
  assert.ok(Math.abs(larger.areaHa / summary.areaHa - 4) < 0.001);
});

test('area respects holes, separate polygon parts, altitude and reversed ring winding', () => {
  const exterior = square(0, 0, 0.01);
  const hole = square(0.002, 0.002, 0.001);
  const first = summarizeDemoGeometry(polygon(exterior));
  const holeArea = summarizeDemoGeometry(polygon(hole)).areaHa;
  const geometry = { type: 'MultiPolygon', coordinates: [
    [exterior.map(point => [...point, 3]), [...hole].reverse()],
    [square(0.02, 0, 0.01)],
  ] };
  const summary = summarizeDemoGeometry(geometry);
  assert.ok(Math.abs(summary.areaHa - (first.areaHa * 2 - holeArea)) < 0.001);
  assert.equal(summary.vertices, 12);
  assert.ok(Math.abs(summarizeDemoGeometry(polygon([...exterior].reverse())).areaHa - first.areaHa) < 0.0001);
});

test('empty, open, zero-area, repeated-point and self-crossing boundaries cannot generate a demo', () => {
  for (const geometry of [null, { type: 'Point', coordinates: [0, 0] },
    { type: 'Polygon', coordinates: [] }, polygon([]), polygon([[0, 0], [1, 0], [1, 1], [0, 1]]),
    polygon([[0, 0], [1, 1], [2, 2], [0, 0]]),
    polygon([[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]),
    polygon([[0, 0], [0, 0], [1, 1], [0, 1], [0, 0]]),
    polygon([[0, 0], [1, 0], [Infinity, 1], [0, 0]]),
    polygon([[0, 0], [181, 0], [1, 1], [0, 0]])]) {
    assert.throws(() => summarizeDemoGeometry(geometry));
  }
});

test('scripted explanation uses the actual outline but never claims measured soil or model output', () => {
  const summary = summarizeDemoGeometry(DEMO_PARCEL);
  const explanation = buildDemoExplanation(summary).join('\n');
  assert.match(explanation, new RegExp(`${summary.areaHa.toFixed(2)} hectares`));
  assert.match(explanation, /assumptions, not conditions detected/);
  assert.match(explanation, /No satellite, soil or weather measurements were fetched/);
  assert.match(explanation, /not a live LLM analysis/);
  assert.match(buildDemoExplanation({ ...summary, latitude: -10, longitude: -20 })[0], /10.0000 S, 20.0000 W/);
});
