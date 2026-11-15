import { test, expect } from '@playwright/test';

const apiOrigin = process.env.TEST_API_ORIGIN;
const frontendOrigin = process.env.TEST_FRONTEND_ORIGIN || 'http://127.0.0.1:1080';
if (!apiOrigin) throw new Error('Set TEST_API_ORIGIN to the real, prepared backend used by the production build.');

test('field geometry and canonical values reconcile with actual API records', async ({ page, request }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('#connection-status')).toContainText('Connected');
  await expect(page.locator('#global-plot-select')).toBeEnabled();
  const fieldId = await page.locator('#global-plot-select').inputValue();
  expect(fieldId).not.toBe('');
  const response = await request.get(`${apiOrigin}/api/v1/fields/${encodeURIComponent(fieldId)}`);
  expect(response.ok()).toBeTruthy();
  const field = (await response.json()).data;
  await page.getByRole('button', { name: 'My Land', exact: true }).click();
  await expect(page.locator('#boundary-select')).toBeEnabled();
  if (field.boundary_versions.length > 1) {
    await expect(page.locator('#field-status')).toContainText('Select one explicitly');
    await expect(page.locator('#api-map')).toBeHidden();
  }
  await page.locator('#boundary-select').selectOption(field.boundary_versions[0].boundary_id);
  await expect(page.locator('#field-status')).toHaveText('Stored boundary loaded.');
  await expect(page.locator('#api-map .leaflet-overlay-pane path')).toHaveCount(1);
  await page.getByRole('button', { name: 'Land Analysis', exact: true }).click();
  await expect(page.locator('#observations-body tr')).toHaveCount(50);
  const observations = (await (await request.get(
    `${apiOrigin}/api/v1/fields/${encodeURIComponent(fieldId)}/observations?limit=50`,
  )).json()).data;
  const first = observations[0];
  await expect(page.locator('#observations-body tr').first()).toContainText(first.variable_id);
  await expect(page.locator('#observations-body tr').first()).toContainText(String(first.scientific_record.value_numeric));
  await expect(page.locator('#observations-body tr').first()).toContainText(first.validation_status);
  await page.locator('#observations-body button').first().click();
  await expect(page.locator('#evidence-details')).toContainText(first.canonical_observation_id);
  await expect(page.locator('#evidence-details')).toContainText('source_record_locator');
  await page.getByRole('button', { name: 'Next page', exact: true }).click();
  await expect(page.locator('#observations-status')).toContainText('Page 2');
  await page.getByRole('button', { name: 'Previous page', exact: true }).click();
  await expect(page.locator('#observations-status')).toContainText('Page 1');
  expect(errors).toEqual([]);
});

test('empty, invalid and racing filters never restore old records', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#global-plot-select')).toBeEnabled();
  await page.getByRole('button', { name: 'Land Analysis', exact: true }).click();
  await expect(page.locator('#observations-body tr')).toHaveCount(50);
  await page.locator('#validation-filter').selectOption('accepted');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await expect(page.locator('#observations-status')).toContainText('No matching observations');
  await expect(page.locator('#observations-body tr')).toHaveCount(0);
  await page.locator('#start-date').fill('2025-01-01');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await expect(page.locator('#observations-status')).toContainText('start_date/end_date');
  await page.locator('#start-date').fill('');
  await page.locator('#validation-filter').selectOption('all');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await page.locator('#validation-filter').selectOption('accepted');
  await page.getByRole('button', { name: 'Apply filters', exact: true }).click();
  await expect(page.locator('#observations-status')).toContainText('No matching observations');
  await expect(page.locator('#observations-body tr')).toHaveCount(0);
});

test('all seven views are usable and unsupported capabilities never activate demos', async ({ page }) => {
  await page.goto('/');
  for (const label of ['Dashboard', 'My Land', 'Land Analysis', 'Crop Recommendations',
    'Market Intelligence', 'Planting Plans', 'My Profile']) {
    await page.getByRole('button', { name: label, exact: true }).click();
    await expect(page.locator('.view-section.active')).toBeVisible();
  }
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
  const html = await page.content();
  expect(html).not.toContain('Shivalingaiah');
  expect(html).not.toContain('41,732');
  expect(html).not.toContain('100% accurate');
  await expect(page.getByRole('button', { name: 'Sign in', exact: true })).toHaveCount(0);
});

test('network failure is explicit and reconnect restores real data', async ({ page }) => {
  await page.route(`${apiOrigin}/api/v1/**`, route => route.abort());
  await page.goto('/');
  await expect(page.locator('#connection-status')).toContainText('unreachable');
  await expect(page.locator('#global-plot-select')).toBeDisabled();
  await expect(page.locator('#observations-body tr')).toHaveCount(0);
  await page.unroute(`${apiOrigin}/api/v1/**`);
  await page.getByRole('button', { name: 'Reconnect', exact: true }).click();
  await expect(page.locator('#connection-status')).toContainText('Connected');
  await expect(page.locator('#global-plot-select')).toBeEnabled();
});

test('browser origin and request failures cannot become fake scientific data', async ({ page }) => {
  // Transport-only interception: no provider or agricultural payload is fabricated.
  await page.route(`${apiOrigin}/api/v1/workspace`, route => route.fulfill({
    status: 200, contentType: 'text/html', body: '<h1>Upstream failure</h1>',
    headers: { 'Access-Control-Allow-Origin': frontendOrigin },
  }));
  await page.goto('/');
  await expect(page.locator('#connection-status')).toContainText('invalid JSON');
  await expect(page.locator('#global-plot-select')).toBeDisabled();
  await expect(page.locator('#observations-body tr')).toHaveCount(0);
});

test('untrusted field labels remain inert text and mobile navigation stays usable', async ({ page, request }) => {
  const realFields = await (await request.get(`${apiOrigin}/api/v1/fields`)).json();
  expect(realFields.data.length).toBeGreaterThan(0);
  // Use real geometry/data unchanged; only inject an adversarial user-text label.
  const label = '<img src=x onerror="window.executedUserText=true">';
  realFields.data[0].name = label;
  await page.route(`${apiOrigin}/api/v1/fields`, route => route.fulfill({
    status: 200, contentType: 'application/json', body: JSON.stringify(realFields),
    headers: { 'Access-Control-Allow-Origin': frontendOrigin },
  }));
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('#global-plot-select')).toBeEnabled();
  await expect(page.locator('#global-plot-select option').nth(1)).toHaveText(label);
  expect(await page.evaluate(() => window.executedUserText)).toBeUndefined();
  await page.getByRole('button', { name: 'Land Analysis', exact: true }).click();
  await expect(page.locator('#view-landanalysis')).toBeVisible();
  await expect(page.locator('#observations-body tr')).toHaveCount(50);
});
