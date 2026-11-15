import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';

const api = process.env.TEST_API_ORIGIN;
const origin = process.env.TEST_FRONTEND_ORIGIN;
if (process.env.TEST_WRITES_ISOLATED !== '1') throw new Error('Field writes require the isolated backend browser harness.');

async function openLand(page) {
  await page.goto('/');
  await expect(page.locator('#global-plot-select')).toBeEnabled();
  await page.getByRole('button', { name: 'My Land', exact: true }).click();
  await expect(page.locator('#boundary-select')).toBeEnabled();
  const boundary = await page.locator('#boundary-select option').nth(1).getAttribute('value');
  await page.locator('#boundary-select').selectOption(boundary);
  await expect(page.locator('#field-status')).toHaveText('Stored boundary loaded.');
}

async function archiveOwned(request, identifier) {
  const record = await request.get(`${api}/api/v1/fields/${identifier}`);
  if (record.status() === 404) return;
  expect(record.ok()).toBeTruthy();
  const archived = await request.delete(`${api}/api/v1/fields/${identifier}`, {
    headers: { Origin: origin, 'If-Match': record.headers().etag },
  });
  expect(archived.status()).toBe(200);
}

async function confirmPreview(page, request) {
  await expect(page.locator('#confirm-import')).toBeEnabled();
  const pending = page.waitForResponse(response => response.url().startsWith(`${api}/api/v1/imports/`)
    && response.url().endsWith('/confirm') && response.request().method() === 'POST');
  await page.locator('#confirm-import').click();
  const response = await pending;
  expect(response.status()).toBe(202);
  const jobId = (await response.json()).data.job_id;
  await expect(page.locator('#job-status')).toContainText('import_confirm: succeeded');
  const job = (await (await request.get(`${api}/api/v1/jobs/${jobId}`)).json()).data;
  return job.result.fields[0].field_id;
}

test('drawn KML is previewed, confirmed, renamed and archived without inventing evidence', async ({ page, request }) => {
  await openLand(page);
  await page.getByRole('button', { name: 'Dashboard', exact: true }).click();
  await page.locator('#btn-dash-add-plot').click();
  await expect(page.locator('#view-myland')).toBeVisible();
  await expect(page.locator('#draw-helper-banner')).toBeVisible();
  await page.locator('#field-name').fill('Browser-drawn boundary ' + randomUUID());
  const map = page.locator('#api-map');
  await map.scrollIntoViewIfNeeded();
  const box = await map.boundingBox();
  for (const [x, y] of [[0.35, 0.35], [0.65, 0.35], [0.65, 0.65], [0.35, 0.65]]) {
    await map.click({ position: { x: box.width * x, y: box.height * y } });
  }
  await expect(page.locator('#draw-points-count')).toHaveText('4 points');
  await page.locator('#btn-undo-drawing').click();
  await expect(page.locator('#draw-points-count')).toHaveText('3 points');
  await map.click({ position: { x: box.width * .35, y: box.height * .65 } });
  await page.locator('#btn-finish-drawing').click();
  const createdResponse = page.waitForResponse(response =>
    new URL(response.url()).pathname === '/api/v1/imports' && response.request().method() === 'POST');
  await page.locator('#save-field').click();
  const created = await createdResponse;
  expect(created.status()).toBe(202);
  expect(created.request().headers()['content-type']).toBe('application/vnd.google-earth.kml+xml');
  const importId = (await created.json()).data.resource_id;
  const source = await request.get(`${api}/api/v1/imports/${importId}/download`);
  expect(await source.text()).toContain('<kml xmlns="http://www.opengis.net/kml/2.2">');
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  const identifier = await confirmPreview(page, request);
  try {
    await expect(page.locator('#global-plot-select')).toHaveValue(identifier);
    await expect(page.locator('#field-write-status')).toHaveText('KML saved; AI analysis unavailable.');
    const stored = (await (await request.get(`${api}/api/v1/fields/${identifier}`)).json()).data;
    expect(stored.geometry.coordinates[0]).toHaveLength(5);
    expect(stored.area_m2).toBeGreaterThan(0);
    const observations = await request.get(`${api}/api/v1/fields/${identifier}/observations`);
    expect((await observations.json()).data).toEqual([]);
    await page.locator('#edit-field').click();
    await page.locator('#field-name').fill('Renamed shared boundary');
    await page.locator('#save-field').click();
    await expect(page.locator('#field-editor')).toBeHidden();
    await expect(page.locator('#field-details')).toContainText('Renamed shared boundary');
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#archive-field').click();
    await expect(page.locator('#field-write-status')).toContainText('Field archived');
    expect((await request.get(`${api}/api/v1/fields/${identifier}`)).status()).toBe(404);
  } finally { await archiveOwned(request, identifier); }
});

test('preview requires confirmation and real KMZ downloads resume across page reloads', async ({ page, request }) => {
  await openLand(page);
  const before = (await (await request.get(`${api}/api/v1/fields`)).json()).data;
  const id = await page.locator('#global-plot-select').inputValue();
  const boundary = await page.locator('#boundary-select').inputValue();
  const record = (await (await request.get(`${api}/api/v1/fields/${id}?boundary_id=${boundary}`)).json()).data;
  const content = { type: 'FeatureCollection', features: [{ type: 'Feature', id: 'unchanged-provider-shape',
    geometry: record.geometry, properties: { name: 'Browser import ' + randomUUID(),
      source_note: 'Unchanged real geometry, explicitly copied for integration acceptance' } }] };
  await page.locator('#btn-upload-boundary').click();
  await page.locator('#boundary-file').setInputFiles({
    name: 'reference.geojson', mimeType: 'application/geo+json', buffer: Buffer.from(JSON.stringify(content)),
  });
  await page.locator('#import-namespace').fill('browser-' + randomUUID());
  await page.locator('#preview-import').click();
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  expect((await (await request.get(`${api}/api/v1/fields`)).json()).data).toHaveLength(before.length);
  await expect(page.locator('#new-field')).toBeDisabled();
  await expect(page.locator('#export-boundary')).toBeDisabled();
  await page.getByRole('button', { name: 'View preview', exact: true }).click();
  await expect(page.locator('#api-map path[stroke="#b96b16"]')).toHaveCount(1);
  const previewJob = new URL(page.url()).searchParams.get('job');
  const preview = (await (await request.get(`${api}/api/v1/jobs/${previewJob}`)).json()).data;
  await page.locator('#close-preview').click();
  expect(new URL(page.url()).searchParams.has('job')).toBeFalsy();
  await expect(page.locator('#new-field')).toBeEnabled();
  const retained = await request.get(`${api}/api/v1/imports/${preview.resource_id}/download`);
  expect((await retained.body()).equals(Buffer.from(JSON.stringify(content)))).toBeTruthy();
  await page.locator('#job-tools summary').click();
  await page.locator('#resume-job-id').fill(previewJob);
  await page.locator('#resume-job').click();
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  await page.reload();
  await page.getByRole('button', { name: 'My Land', exact: true }).click();
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  await page.locator('#confirm-import').click();
  await expect(page.locator('#job-status')).toContainText('import_confirm: succeeded');
  const jobId = new URL(page.url()).searchParams.get('job');
  const job = (await (await request.get(`${api}/api/v1/jobs/${jobId}`)).json()).data;
  const importedId = job.result.fields[0].field_id;
  try {
    await expect(page.locator('#global-plot-select')).toHaveValue(importedId);
    await page.locator('#export-tools summary').click();
    await page.locator('#export-format').selectOption('kmz');
    await page.locator('#export-boundary').click();
    await expect(page.locator('#download-export')).toBeVisible();
    await page.reload();
    await page.getByRole('button', { name: 'My Land', exact: true }).click();
    await expect(page.locator('#download-export')).toBeEnabled();
    const completedId = new URL(page.url()).searchParams.get('job');
    const completed = (await (await request.get(`${api}/api/v1/jobs/${completedId}`)).json()).data;
    const event = page.waitForEvent('download');
    await page.locator('#download-export').click();
    const download = await event;
    expect(download.suggestedFilename()).toBe(completed.resource_id + '.kmz');
    const bytes = await readFile(await download.path());
    const server = await request.get(`${api}/api/v1/exports/${completed.resource_id}/download`);
    expect(bytes.equals(await server.body())).toBeTruthy();
    expect(bytes.subarray(0, 2).toString()).toBe('PK');
  } finally { await archiveOwned(request, importedId); }
});

test('lost KML acknowledgments replay identical bytes and known jobs resume without another POST', async ({ page, request }) => {
  await openLand(page);
  const id = await page.locator('#global-plot-select').inputValue();
  const boundary = await page.locator('#boundary-select').inputValue();
  const geometry = (await (await request.get(`${api}/api/v1/fields/${id}?boundary_id=${boundary}`)).json()).data.geometry;
  let savedId;
  let previewId;
  const keys = [];
  const payloads = [];
  const imports = url => url.origin === api && url.pathname === '/api/v1/imports';
  page.on('request', request => {
    if (imports(new URL(request.url())) && request.method() === 'POST') {
      keys.push(request.headers()['idempotency-key']);
      payloads.push(request.postDataBuffer());
    }
  });
  await page.route(imports, async route => {
    if (route.request().method() !== 'POST') { await route.continue(); return; }
    const response = await route.fetch();
    previewId = (await response.json()).data.job_id;
    await route.abort();
  });
  await page.locator('#new-field').click();
  const name = 'Ambiguous create ' + randomUUID();
  await page.locator('#field-name').fill(name);
  await page.locator('#field-geometry').fill(JSON.stringify(geometry));
  await page.locator('#save-field').click();
  await expect(page.locator('#field-write-status')).toContainText('Retry the same submission');
  try {
    await expect(page.locator('#field-name')).toHaveValue(name);
    await expect(page.locator('#field-name')).toBeDisabled();
    await page.unroute(imports);
    await page.route(`${api}/api/v1/jobs/**`, route => route.abort());
    await page.locator('#save-field').click();
    await expect(page.locator('#job-status')).toContainText('The server job was not cancelled');
    await expect(page.locator('#save-field')).toHaveText('Resume KML preview');
    await expect(page.locator('#field-name')).toBeDisabled();
    await expect(page.locator('#preview-import')).toBeDisabled();
    expect(new URL(page.url()).searchParams.get('job')).toBe(previewId);
    await page.unroute(`${api}/api/v1/jobs/**`);
    await page.locator('#save-field').click();
    await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
    const before = (await (await request.get(`${api}/api/v1/fields`)).json()).data;
    expect(before.filter(record => record.name === name)).toHaveLength(0);
    savedId = await confirmPreview(page, request);
    await expect(page.locator('#global-plot-select')).toHaveValue(savedId);
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
    expect(payloads[0].equals(payloads[1])).toBeTruthy();
    const records = (await (await request.get(`${api}/api/v1/fields`)).json()).data;
    expect(records.filter(record => record.name === name)).toHaveLength(1);
  } finally { if (savedId) await archiveOwned(request, savedId); }
});

test('stale field edits retain their draft and require explicit reload', async ({ page, request }) => {
  await openLand(page);
  const id = await page.locator('#global-plot-select').inputValue();
  const boundary = await page.locator('#boundary-select').inputValue();
  const original = (await (await request.get(`${api}/api/v1/fields/${id}?boundary_id=${boundary}`)).json()).data;
  const response = await request.post(`${api}/api/v1/fields`, {
    headers: { Origin: origin, 'Idempotency-Key': randomUUID() },
    data: { project_id: original.project_id, name: 'Conflict acceptance copy', geometry: original.geometry },
  });
  const identifier = (await response.json()).data.field_id;
  try {
    await page.getByRole('button', { name: 'Reconnect', exact: true }).click();
    await expect(page.locator(`#global-plot-select option[value="${identifier}"]`)).toHaveCount(1);
    await page.locator('#global-plot-select').selectOption(identifier);
    await expect(page.locator('#edit-field')).toBeEnabled();
    await page.locator('#edit-field').click();
    await page.locator('#field-name').fill('Retained field draft');
    const current = await request.get(`${api}/api/v1/fields/${identifier}`);
    expect((await request.patch(`${api}/api/v1/fields/${identifier}`, {
      headers: { Origin: origin, 'If-Match': current.headers().etag }, data: { name: 'Other visitor change' },
    })).status()).toBe(200);
    await page.locator('#save-field').click();
    await expect(page.locator('#field-write-status')).toContainText('Draft retained');
    await expect(page.locator('#field-name')).toHaveValue('Retained field draft');
    await expect(page.locator('#save-field')).toBeDisabled();
    await page.locator('#cancel-field').click();
    await expect(page.locator('#field-details')).toContainText('Other visitor change');
  } finally { await archiveOwned(request, identifier); }
});

test('explicit complex geometry retains all parts, holes and altitude through map and download', async ({ page, request }) => {
  // Isolated user-input topology probe, not authentic provider or agricultural evidence.
  const geometry = { type: 'MultiPolygon', coordinates: [
    [[[10, 10, 3], [14, 10, 4], [14, 14, 5], [10, 14, 6], [10, 10, 3]],
      [[11, 11, 3], [11, 12, 3], [12, 12, 3], [12, 11, 3], [11, 11, 3]]],
    [[[15, 10, 3], [16, 10, 3], [16, 11, 3], [15, 11, 3], [15, 10, 3]]],
  ] };
  await openLand(page);
  await page.locator('#new-field').click();
  await page.locator('#field-name').fill('Topology-only input probe, not a real field');
  await page.locator('#field-geometry').fill(JSON.stringify(geometry));
  await page.locator('#save-field').click();
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  const identifier = await confirmPreview(page, request);
  try {
    await expect(page.locator('#global-plot-select')).toHaveValue(identifier);
    await expect(page.locator('#api-map .leaflet-overlay-pane path')).toHaveCount(1);
    const stored = (await (await request.get(`${api}/api/v1/fields/${identifier}`)).json()).data;
    expect(stored.geometry.coordinates.map(polygon => polygon.length)).toEqual([2, 1]);
    await page.locator('#export-tools summary').click();
    await page.locator('#export-format').selectOption('geojson');
    await page.locator('#export-boundary').click();
    await expect(page.locator('#download-export')).toBeVisible();
    const event = page.waitForEvent('download');
    await page.locator('#download-export').click();
    const download = await event;
    const exported = JSON.parse(await readFile(await download.path(), 'utf8'));
    expect(exported.features[0].geometry).toEqual(geometry);
  } finally { await archiveOwned(request, identifier); }
});

test('rejected KML keeps its editable draft and corrected geometry gets a fresh preview', async ({ page, request }) => {
  await openLand(page);
  const id = await page.locator('#global-plot-select').inputValue();
  const boundary = await page.locator('#boundary-select').inputValue();
  const geometry = (await (await request.get(`${api}/api/v1/fields/${id}?boundary_id=${boundary}`)).json()).data.geometry;
  const before = (await (await request.get(`${api}/api/v1/fields`)).json()).data.length;
  const keys = [];
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/v1/imports' && request.method() === 'POST') {
      keys.push(request.headers()['idempotency-key']);
    }
  });
  await page.locator('#new-field').click();
  const name = 'Topology rejection diagnostic - not agricultural evidence';
  await page.locator('#field-name').fill(name);
  const invalid = { type: 'Polygon', coordinates: [[[10, 10], [11, 11], [11, 10], [10, 11], [10, 10]]] };
  await page.locator('#field-geometry').fill(JSON.stringify(invalid));
  await page.locator('#save-field').click();
  await expect(page.locator('#boundary-preview')).toContainText('0 valid candidates; 1 rejected');
  await expect(page.locator('#field-write-status')).toContainText('Correct the draft');
  await expect(page.locator('#field-name')).toBeEnabled();
  await expect(page.locator('#field-name')).toHaveValue(name);
  await expect(page.locator('#field-geometry')).toHaveValue(JSON.stringify(invalid));
  expect((await (await request.get(`${api}/api/v1/fields`)).json()).data).toHaveLength(before);
  await page.locator('#field-geometry').fill(JSON.stringify(geometry));
  await page.locator('#save-field').click();
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  expect(keys).toHaveLength(2);
  expect(keys[0]).not.toBe(keys[1]);
  const identifier = await confirmPreview(page, request);
  try { await expect(page.locator('#global-plot-select')).toHaveValue(identifier); }
  finally { await archiveOwned(request, identifier); }
});
