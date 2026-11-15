import { test, expect } from '@playwright/test';
import { validateResponse } from '../../src/api/validation.js';

async function openDemo(page, { reducedMotion = false } = {}) {
  if (reducedMotion) await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.route('**/api/v1/**', route => route.abort());
  await page.route('https://*.tile.openstreetmap.org/**', route => route.abort());
  await page.goto('/?demo=rotation');
  await expect(page.locator('#crop-rotation-demo')).toBeVisible();
  await expect(page.locator('.connection-bar')).toBeHidden();
}

async function draw(page, points) {
  const map = page.locator('#rotation-map');
  await page.locator('#rotation-draw').click();
  await map.scrollIntoViewIfNeeded();
  const box = await map.boundingBox();
  for (const [x, y] of points) {
    await map.click({ position: { x: box.width * x, y: box.height * y } });
  }
}

test('example parcel runs without backend or map tiles and streams a clearly labeled rotation', async ({ page }) => {
  const errors = [];
  const writes = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (['POST', 'PATCH', 'DELETE', 'PUT'].includes(request.method())) writes.push(request.url());
  });
  await openDemo(page);
  await expect(page.locator('#rotation-scan')).toBeDisabled();
  await expect(page.locator('#rotation-use-field')).toBeDisabled();
  await page.locator('#rotation-sample').click();
  const area = (await page.locator('#rotation-input-summary').textContent()).split(' ha')[0];
  await page.locator('#rotation-scan').click();
  await expect(page.locator('#rotation-scan-panel')).toBeVisible();
  await expect(page.locator('#rotation-scan')).toBeDisabled();
  await expect(page.locator('#rotation-report')).toBeVisible();
  await expect(page.locator('#rotation-report-area')).toHaveText(`${area} ha`);
  await expect(page.locator('.rotation-crop-card')).toHaveCount(3);
  await expect(page.locator('.rotation-crop-card.rice')).toContainText('JUL - DEC');
  await expect(page.locator('.rotation-crop-card.pulse')).toContainText('FEB - APR');
  await expect(page.locator('.rotation-crop-card.rest')).toContainText('MAY - JUN');
  await expect(page.locator('#rotation-explanation-text p')).not.toHaveCount(0);
  await expect(page.locator('#rotation-explanation-text')).toHaveAttribute('aria-busy', 'true');
  await page.locator('#rotation-reveal').click();
  await expect(page.locator('#rotation-explanation-text')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#rotation-explanation-text p')).toHaveCount(6);
  await expect(page.locator('#rotation-explanation-text')).toContainText('assumptions, not conditions detected');
  await expect(page.locator('#rotation-explanation-text')).toContainText('not a live LLM');
  await expect(page.locator('.rotation-disclosure')).toContainText('simulated scan');
  await expect(page.locator('#rotation-tile-status')).toContainText('unavailable');
  expect(writes).toEqual([]);
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  expect(errors).toEqual([]);
});

test('drawn map polygon is required, propagated to report, and replaceable', async ({ page }) => {
  await openDemo(page, { reducedMotion: true });
  await draw(page, [[.35, .35], [.65, .35]]);
  await page.locator('#rotation-finish').click();
  await expect(page.locator('#rotation-selection-status')).toContainText('at least three');
  await expect(page.locator('#rotation-scan')).toBeDisabled();
  const map = page.locator('#rotation-map');
  const box = await map.boundingBox();
  await map.click({ position: { x: box.width * .65, y: box.height * .65 } });
  await map.click({ position: { x: box.width * .35, y: box.height * .65 } });
  await page.locator('#rotation-finish').click();
  await expect(page.locator('#rotation-input-summary')).toContainText('4 boundary points / Your drawn plot');
  const firstArea = (await page.locator('#rotation-input-summary').textContent()).split(' ha')[0];
  await page.locator('#rotation-scan').click();
  await expect(page.locator('#rotation-report-area')).toHaveText(`${firstArea} ha`);
  await expect(page.locator('#rotation-explanation-text')).toContainText(`${firstArea} hectares`);
  await expect(page.locator('#rotation-reveal')).toBeHidden();
  await page.locator('#rotation-edit').click();
  await expect(page.locator('#rotation-report')).toBeHidden();
  await draw(page, [[.4, .4], [.55, .4], [.55, .55], [.4, .55]]);
  await page.locator('#rotation-finish').click();
  const secondArea = (await page.locator('#rotation-input-summary').textContent()).split(' ha')[0];
  expect(secondArea).not.toBe(firstArea);
  await page.locator('#rotation-scan').click();
  await expect(page.locator('#rotation-report-area')).toHaveText(`${secondArea} ha`);
  await expect(page.locator('#rotation-explanation-text')).toContainText(`${secondArea} hectares`);
});

test('crossed outline is rejected and loading another boundary cancels an in-flight scan', async ({ page }) => {
  await openDemo(page);
  await page.clock.install();
  await draw(page, [[.35, .35], [.65, .65], [.35, .65], [.65, .35]]);
  await page.locator('#rotation-finish').click();
  await expect(page.locator('#rotation-selection-status')).toContainText('crosses itself');
  await expect(page.locator('#rotation-scan')).toBeDisabled();
  await page.locator('#rotation-sample').click();
  await page.locator('#rotation-scan').click();
  await expect(page.locator('#rotation-scan-panel')).toBeVisible();
  await page.locator('#rotation-draw').click();
  await page.clock.runFor(3000);
  await expect(page.locator('#rotation-scan-panel')).toBeHidden();
  await expect(page.locator('#rotation-report')).toBeHidden();
  await expect(page.locator('#rotation-scan')).toBeDisabled();
});

test('mobile demo navigation, calendar scrolling and explanation remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openDemo(page, { reducedMotion: true });
  for (const label of ['My Land', 'Land Analysis', 'Market Intelligence', 'Planting Plans', 'My Profile', 'Dashboard']) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.locator('.view-section.active')).toBeVisible();
  }
  await expect(page.locator('.connection-bar')).toBeVisible();
  await page.getByRole('button', { name: /Try crop rotation demo/ }).click();
  await expect(page.locator('#rotation-map')).toBeVisible();
  await page.locator('#rotation-sample').click();
  await page.locator('#rotation-scan').click();
  await expect(page.locator('#rotation-report')).toBeVisible();
  await expect(page.locator('#rotation-explanation-text p')).toHaveCount(6);
  const dimensions = await page.evaluate(() => ({
    width: innerWidth, content: document.documentElement.scrollWidth,
    main: document.querySelector('.main-content').getBoundingClientRect().width,
    calendar: document.querySelector('.rotation-calendar').clientWidth,
    calendarContent: document.querySelector('.rotation-calendar').scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.width);
  expect(dimensions.main).toBeGreaterThanOrEqual(dimensions.width - 1);
  expect(dimensions.calendarContent).toBeGreaterThan(dimensions.calendar);
  await page.locator('#rotation-edit').click();
  await expect(page.locator('#rotation-scan')).toBeEnabled();
});

test('scripted streaming completes automatically without duplicating paragraphs', async ({ page }) => {
  await openDemo(page);
  await page.clock.install();
  await page.locator('#rotation-sample').click();
  await page.locator('#rotation-scan').click();
  await page.clock.runFor(2500);
  await expect(page.locator('#rotation-explanation-text')).toHaveAttribute('aria-busy', 'true');
  await page.clock.runFor(10000);
  await expect(page.locator('#rotation-explanation-text')).toHaveAttribute('aria-busy', 'false');
  await expect(page.locator('#rotation-explanation-text p')).toHaveCount(6);
  await expect(page.locator('#rotation-reveal')).toBeHidden();
  await expect(page.locator('#rotation-stream-state')).toHaveText('Explanation complete');
});

test('selected field input preserves holes and treats field names as text', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  // Synthetic UI boundary fixture only, not provider data or scientific acceptance.
  const field = {
    field_id: 'demo-ui-test', project_id: 'demo-test', name: '<img src=x onerror="window.executedUserText=true">',
    current_boundary_id: 'test-boundary', selected_boundary_id: 'test-boundary', geometry_status: 'available',
    boundary_versions: [{ boundary_id: 'test-boundary', source_asset_id: 'test-input' }],
    geometry: { type: 'Polygon', coordinates: [
      [[76.899, 12.522], [76.901, 12.522], [76.901, 12.524], [76.899, 12.524], [76.899, 12.522]],
      [[76.8995, 12.5225], [76.900, 12.5225], [76.900, 12.523], [76.8995, 12.523], [76.8995, 12.5225]],
    ] },
    metric_crs: null, area_m2: null, area_ha: null, perimeter_m: null, representative_point: null, repair_notes: null,
  };
  const meta = { api_version: 'v1', request_id: 'demo-ui-test' };
  const responses = {
    '/api/v1/workspace': { data: {
      access_mode: 'shared_trusted_network', contract_revision: 'shared-workspace-1', project_ids: ['demo-test'],
      capabilities: [{ capability_id: 'fields', state: 'ready', operation_ids: [], reason: null }],
    }, meta },
    '/api/v1/fields': { data: [field], meta: { ...meta, next_cursor: null } },
    '/api/v1/fields/demo-ui-test': { data: field, meta },
  };
  expect(validateResponse('FieldResponse', responses['/api/v1/fields/demo-ui-test'])).toBe(true);
  await page.route('https://*.tile.openstreetmap.org/**', route => route.abort());
  await page.route('**/api/v1/**', route => {
    const body = responses[new URL(route.request().url()).pathname];
    return body ? route.fulfill({
      json: body, headers: { 'Access-Control-Allow-Origin': route.request().headers().origin || '*' },
    }) : route.abort();
  });
  await page.goto('/');
  await expect(page.locator('#connection-status')).toContainText('Connected');
  await page.getByRole('button', { name: 'My Land', exact: true }).click();
  await expect(page.locator('#field-status')).toHaveText('Stored boundary loaded.');
  await page.getByRole('button', { name: /Open crop rotation demo/ }).click();
  await page.locator('#rotation-use-field').click();
  await expect(page.locator('#rotation-input-summary')).toContainText('8 boundary points');
  await page.locator('#rotation-scan').click();
  await expect(page.locator('#rotation-report-location')).toContainText('<img src=x');
  expect(await page.evaluate(() => window.executedUserText)).toBeUndefined();
  await expect(page.locator('img[src="x"]')).toHaveCount(0);
});
