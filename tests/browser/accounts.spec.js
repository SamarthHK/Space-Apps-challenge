import { test, expect } from '@playwright/test';

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
