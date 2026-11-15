import { test, expect } from '@playwright/test';

const api = process.env.TEST_API_ORIGIN;
const origin = process.env.TEST_FRONTEND_ORIGIN || 'http://127.0.0.1:1080';

async function openProfile(page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'My Profile', exact: true }).click();
  await expect(page.locator('#profile-name')).toBeEnabled();
}

test('shared profile survives independent browser sessions and keeps source inspection', async ({ page, browser }) => {
  await openProfile(page);
  await page.locator('#profile-name').fill('Shared browser integration');
  await page.locator('#profile-preferred_language').selectOption('kn');
  await page.getByRole('button', { name: 'Save shared profile', exact: true }).click();
  await expect(page.locator('#profile-status')).toContainText('Saved shared profile');
  const context = await browser.newContext({ baseURL: origin });
  const other = await context.newPage();
  await openProfile(other);
  await expect(other.locator('#profile-name')).toHaveValue('Shared browser integration');
  await expect(other.locator('#profile-preferred_language')).toHaveValue('kn');
  expect(await context.cookies()).toEqual([]);
  await page.getByRole('button', { name: 'Land Analysis', exact: true }).click();
  await expect(page.locator('#observations-body tr')).toHaveCount(50);
  await page.locator('#observations-body button').first().click();
  await expect(page.locator('#evidence-details')).toContainText('source_record_locator');
  await context.close();
});

test('conflicts and reconnect preserve drafts until an explicit reload', async ({ page, request }) => {
  await openProfile(page);
  const before = await request.get(`${api}/api/v1/profile`);
  const updated = await request.patch(`${api}/api/v1/profile`, {
    headers: { Origin: origin, 'If-Match': before.headers().etag },
    data: { name: 'Changed by another workspace visitor' },
  });
  expect(updated.status()).toBe(200);
  await page.locator('#profile-name').fill('Unsaved local draft');
  await page.getByRole('button', { name: 'Reconnect', exact: true }).click();
  await expect(page.locator('#connection-status')).toContainText('Connected');
  await expect(page.locator('#profile-name')).toHaveValue('Unsaved local draft');
  await page.getByRole('button', { name: 'Save shared profile', exact: true }).click();
  await expect(page.locator('#profile-status')).toContainText('changed');
  await expect(page.locator('#profile-name')).toHaveValue('Unsaved local draft');
  await expect(page.getByRole('button', { name: 'Save shared profile', exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'Reload (discards edits)', exact: true }).click();
  await expect(page.locator('#profile-name')).toHaveValue('Changed by another workspace visitor');
});

test('an ambiguous write is not replayed and cannot erase the local draft', async ({ page }) => {
  await openProfile(page);
  let writes = 0;
  await page.route(`${api}/api/v1/profile`, async route => {
    if (route.request().method() === 'PATCH') { writes++; await route.abort(); }
    else await route.continue();
  });
  await page.locator('#profile-name').fill('Retain this draft after transport failure');
  await page.getByRole('button', { name: 'Save shared profile', exact: true }).click();
  await expect(page.locator('#profile-status')).toContainText('Reload before another save');
  await expect(page.locator('#profile-name')).toHaveValue('Retain this draft after transport failure');
  await expect(page.getByRole('button', { name: 'Save shared profile', exact: true })).toBeDisabled();
  expect(writes).toBe(1);
});
