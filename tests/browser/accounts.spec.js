import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const api = process.env.TEST_API_ORIGIN;
const origin = process.env.TEST_FRONTEND_ORIGIN;
const password = 'Disposable private browser acceptance password';
if (process.env.TEST_WRITES_ISOLATED !== '1' || process.env.TEST_AUTH_MODE !== 'accounts') {
  throw new Error('Run private browser acceptance through the isolated backend harness.');
}

async function signUp(page, login) {
  await page.goto('/');
  await expect(page.locator('#account-access')).toBeVisible();
  await page.locator('#account-mode-toggle').click();
  await page.locator('#account-login').fill(login);
  await page.locator('#account-password').fill(password);
  await page.locator('#account-password-confirm').fill(password);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page.locator('#connection-status')).toContainText(`private workspace for ${login}`);
  await expect(page.locator('#fields-status')).toContainText('No saved plots');
}

async function signIn(page, login) {
  await expect(page.locator('#account-access')).toBeVisible();
  await page.locator('#account-login').fill(login);
  await page.locator('#account-password').fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.locator('#connection-status')).toContainText(`private workspace for ${login}`);
}

async function openProfile(page) {
  await page.getByRole('button', { name: 'My Profile', exact: true }).click();
  await expect(page.locator('#profile-name')).toBeEnabled();
  await expect(page.locator('#profile-privacy-notice')).toContainText('private to your signed-in account');
}

async function session(page) {
  const response = await page.request.get(`${api}/api/v1/auth/session`, { headers: { Origin: origin } });
  expect(response.status()).toBe(200);
  return (await response.json()).data;
}

test('private signup and profile persist without exposing them to another browser account', async ({ page, browser }, testInfo) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.locator('#account-access')).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath('private-sign-in.png'), fullPage: true });
  await signUp(page, 'browser-first-owner');
  await openProfile(page);
  await page.locator('#profile-name').fill('Private browser profile');
  await page.getByRole('button', { name: 'Save profile', exact: true }).click();
  await expect(page.locator('#profile-status')).toContainText('Saved profile');
  await expect(page.locator('#header-farmer-name')).toHaveText('Private browser profile');
  const cookies = await page.context().cookies(`${api}/api/v1/auth/session`);
  expect(cookies.length).toBe(1);
  expect(cookies.every(cookie => cookie.httpOnly && cookie.sameSite === 'Strict')).toBeTruthy();
  expect(await page.evaluate(() => [Object.keys(localStorage), Object.keys(sessionStorage)])).toEqual([[], []]);
  const otherContext = await browser.newContext({ baseURL: origin });
  try {
    const other = await otherContext.newPage();
    await other.setViewportSize({ width: 390, height: 844 });
    await other.goto('/');
    await expect(other.locator('#account-access')).toBeVisible();
    expect(await other.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
    await other.screenshot({ path: testInfo.outputPath('private-sign-in-mobile.png'), fullPage: true });
    await signUp(other, 'browser-second-owner');
    await openProfile(other);
    await expect(other.locator('#profile-name')).toHaveValue('');
    const first = await session(page), second = await session(other);
    expect(first.user.id).not.toBe(second.user.id);
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await signIn(page, 'browser-first-owner');
    await openProfile(page);
    await expect(page.locator('#profile-name')).toHaveValue('Private browser profile');
    await expect(other.locator('#profile-name')).toHaveValue('');
    await page.screenshot({ path: testInfo.outputPath('private-profile.png'), fullPage: true });
    expect(errors).toEqual([]);
  } finally { await otherContext.close(); }
});

test('server session revocation clears private drafts before another sign-in', async ({ page }) => {
  await signUp(page, 'browser-revoked-owner');
  await openProfile(page);
  await page.locator('#profile-name').fill('Do not carry this private draft');
  const current = await session(page);
  const response = await page.request.post(`${api}/api/v1/auth/logout`, {
    headers: { Origin: origin, 'X-CSRF-Token': current.csrf_token },
  });
  expect(response.status()).toBe(204);
  await page.getByRole('button', { name: 'Save profile', exact: true }).click();
  await expect(page.locator('#account-access')).toBeVisible();
  await expect(page.locator('#account-status')).toContainText('session ended');
  await expect(page.locator('#app-container')).toBeHidden();
  await expect(page.locator('#profile-name')).toHaveValue('');
  await signIn(page, 'browser-revoked-owner');
  await openProfile(page);
  await expect(page.locator('#profile-name')).toHaveValue('');
});

test('missed account-switch notifications cannot mix records and sign-out clears other tabs', async ({ page, browser }) => {
  await signUp(page, 'browser-switch-first');
  await openProfile(page);
  await page.locator('#profile-name').fill('First account unsaved draft');
  const sibling = await page.context().newPage();
  await sibling.goto('/');
  await expect(sibling.locator('#connection-status')).toContainText('browser-switch-first');
  await openProfile(sibling);
  await sibling.locator('#profile-name').fill('Another stale private draft');
  const otherContext = await browser.newContext({ baseURL: origin });
  try {
    const other = await otherContext.newPage();
    await signUp(other, 'browser-switch-second');
    const bootstrap = await page.request.post(`${api}/api/v1/auth/bootstrap`, { headers: { Origin: origin } });
    expect(bootstrap.status()).toBe(200);
    const switched = await page.request.post(`${api}/api/v1/auth/login`, {
      headers: { Origin: origin, 'X-CSRF-Token': (await bootstrap.json()).data.csrf_token },
      data: { login: 'browser-switch-second', password },
    });
    expect(switched.status()).toBe(200);
    const rejected = page.waitForResponse(response => response.url() === `${api}/api/v1/profile`
      && response.request().method() === 'PATCH');
    await page.getByRole('button', { name: 'Save profile', exact: true }).click();
    expect((await rejected).status()).toBe(409);
    await expect(page.locator('#connection-status')).toContainText('browser-switch-second');
    await openProfile(page);
    await expect(page.locator('#profile-name')).toHaveValue('');
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await expect(page.locator('#account-access')).toBeVisible();
    await expect(sibling.locator('#account-access')).toBeVisible();
    await expect(sibling.locator('#profile-name')).toHaveValue('');
  } finally {
    await sibling.close();
    await otherContext.close();
  }
});

test('a private Earth drawing saves real KML, survives sign-in and denies another account its files', async ({ page, browser }, testInfo) => {
  test.setTimeout(45000);
  await signUp(page, 'browser-kml-owner');
  await page.getByRole('button', { name: 'My Land', exact: true }).click();
  const map = page.locator('#api-map');
  await expect(map).toBeVisible();
  await expect(page.locator('#field-status')).toHaveText('Select a field.');
  await page.locator('#btn-start-drawing').click();
  const name = 'Private <KML> & ownership probe - not a real field';
  await page.locator('#field-name').fill(name);
  await page.locator('#map-longitude').fill('77.59');
  await page.locator('#map-latitude').fill('12.97');
  await page.locator('#center-map').click();
  await expect.poll(() => map.locator('img.leaflet-tile-loaded').evaluateAll(images =>
    images.some(image => image.src.includes('/World_Imagery/MapServer/tile/17/') && image.naturalWidth > 0)),
  { timeout: 15000 }).toBeTruthy();
  await map.scrollIntoViewIfNeeded();
  const box = await map.boundingBox();
  for (const [x, y] of [[.35, .4], [.6, .4], [.6, .65], [.35, .65]]) {
    await map.click({ position: { x: box.width * x, y: box.height * y } });
  }
  await page.locator('#btn-finish-drawing').click();
  const geometry = JSON.parse(await page.locator('#field-geometry').inputValue());
  let bytes;
  await page.route(url => url.origin === api && url.pathname === '/api/v1/imports', async route => {
    if (route.request().method() === 'POST') bytes = route.request().postDataBuffer();
    await route.continue();
  });
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/imports'
    && response.request().method() === 'POST');
  await page.locator('#save-field').click();
  const response = await pending;
  expect(response.status()).toBe(202);
  const submitted = response.request();
  expect(Buffer.isBuffer(bytes)).toBeTruthy();
  expect(submitted.headers()['content-type']).toBe('application/vnd.google-earth.kml+xml');
  const parsed = await page.evaluate(xml => {
    const document = new DOMParser().parseFromString(xml, 'application/xml');
    if (document.querySelector('parsererror')) throw new Error('Drawing did not produce valid XML');
    const namespace = 'http://www.opengis.net/kml/2.2';
    return { namespace: document.documentElement.namespaceURI,
      name: document.getElementsByTagNameNS(namespace, 'name')[0].textContent,
      id: document.getElementsByTagNameNS(namespace, 'Placemark')[0].getAttribute('id'),
      rings: [...document.getElementsByTagNameNS(namespace, 'coordinates')].map(element =>
        element.textContent.trim().split(/\s+/).map(position => position.split(',').map(Number))) };
  }, bytes.toString('utf8'));
  expect(parsed).toEqual({ namespace: 'http://www.opengis.net/kml/2.2', name,
    id: `drawn-${submitted.headers()['idempotency-key']}`, rings: geometry.coordinates });
  const previewJob = (await response.json()).data;
  const importId = previewJob.resource_id;
  await expect(page.locator('#boundary-preview')).toContainText('1 valid candidates');
  expect((await (await page.request.get(`${api}/api/v1/fields`)).json()).data).toEqual([]);
  const preview = (await (await page.request.get(`${api}/api/v1/imports/${importId}`)).json()).data;
  expect(preview.candidates[0].original_geometry).toEqual(geometry);
  expect(preview.sha256).toBe(createHash('sha256').update(bytes).digest('hex'));
  const originalEvent = page.waitForEvent('download');
  await page.locator('#download-import-original').click();
  const originalDownload = await originalEvent;
  expect(originalDownload.suggestedFilename()).toBe(`original_${preview.sha256}.kml`);
  expect((await readFile(await originalDownload.path())).equals(bytes)).toBeTruthy();
  await page.screenshot({ path: testInfo.outputPath('private-kml-preview.png'), fullPage: true });
  await page.locator('#confirm-import').click();
  await expect(page.locator('#field-write-status')).toHaveText('KML saved; AI analysis unavailable.');
  const confirmId = new URL(page.url()).searchParams.get('job');
  const confirmation = (await (await page.request.get(`${api}/api/v1/jobs/${confirmId}`)).json()).data;
  const identifier = confirmation.result.fields[0].field_id;
  await expect(page.locator('#global-plot-select')).toHaveValue(identifier);
  const stored = (await (await page.request.get(`${api}/api/v1/fields/${identifier}`)).json()).data;
  expect(stored.name).toBe(name);
  expect(stored.area_m2).toBeGreaterThan(0);
  expect((await (await page.request.get(`${api}/api/v1/fields/${identifier}/observations`)).json()).data).toEqual([]);
  await page.locator('#export-tools summary').click();
  await page.locator('#export-boundary').click();
  await expect(page.locator('#download-export')).toBeVisible();
  const exportJob = (await (await page.request.get(
    `${api}/api/v1/jobs/${new URL(page.url()).searchParams.get('job')}`)).json()).data;
  const sourcePath = `/fields/${identifier}/boundaries/${stored.selected_boundary_id}/original`;
  const otherContext = await browser.newContext({ baseURL: origin });
  try {
    const other = await otherContext.newPage();
    await signUp(other, 'browser-kml-outsider');
    for (const path of [`/fields/${identifier}`, sourcePath, `/imports/${importId}`, `/imports/${importId}/download`,
      `/jobs/${previewJob.job_id}`, `/jobs/${confirmId}`, `/exports/${exportJob.resource_id}/download`]) {
      expect((await other.request.get(`${api}/api/v1${path}`)).status()).toBe(404);
    }
    await page.reload();
    await expect(page.locator('#global-plot-select')).toHaveValue(identifier);
    await page.getByRole('button', { name: 'Sign out', exact: true }).click();
    await signIn(page, 'browser-kml-owner');
    await page.getByRole('button', { name: 'My Land', exact: true }).click();
    await expect(page.locator('#field-details')).toContainText(name);
    if (!await page.locator('#export-tools').evaluate(element => element.open)) {
      await page.locator('#export-tools summary').click();
    }
    await expect(page.locator('#download-boundary-original')).toBeEnabled();
    const savedEvent = page.waitForEvent('download');
    await page.locator('#download-boundary-original').click();
    const saved = await savedEvent;
    expect((await readFile(await saved.path())).equals(bytes)).toBeTruthy();
    await page.screenshot({ path: testInfo.outputPath('private-saved-plot.png'), fullPage: true });
    await page.getByRole('button', { name: 'Crop Recommendations', exact: true }).click();
    await expect(page.locator('#view-recommendations')).toContainText('AI unavailable');
    expect((await (await other.request.get(`${api}/api/v1/fields`)).json()).data).toEqual([]);
  } finally { await otherContext.close(); }
});
