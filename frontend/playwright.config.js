import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  ...(process.env.TEST_AUTH_MODE === 'accounts'
    ? { testMatch: /accounts\.spec\.js$/ } : { testIgnore: /accounts\.spec\.js$/ }),
  fullyParallel: false,
  workers: 1,
  outputDir: process.env.PLAYWRIGHT_OUTPUT_DIR || 'test-results',
  use: { baseURL: process.env.TEST_FRONTEND_ORIGIN || 'http://127.0.0.1:1080', browserName: 'chromium' },
  webServer: process.env.TEST_FRONTEND_ORIGIN ? undefined : {
    command: 'npm run preview',
    url: 'http://127.0.0.1:1080',
    reuseExistingServer: false,
    env: { FRONTEND_HOST: '127.0.0.1' },
  },
});
