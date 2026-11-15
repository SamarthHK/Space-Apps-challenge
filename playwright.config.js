import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:1080', browserName: 'chromium' },
  webServer: {
    command: 'npm run preview',
    url: 'http://127.0.0.1:1080',
    reuseExistingServer: false,
    env: { FRONTEND_HOST: '127.0.0.1' },
  },
});
