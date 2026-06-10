import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';

export default defineConfig({
  testDir: './tests',
  /* Run tests in files sequentially to avoid sqlite database conflicts */
  fullyParallel: false,
  /* We use 1 worker to ensure that tests running across browsers do not conflict on database state */
  workers: 1,
  /* Increase test timeout for E2E flows */
  timeout: 60000,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list']
  ],
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://127.0.0.1:18080',

    /* Collect trace when retrying a failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'CREATE_TABLES_ON_STARTUP=true DATABASE_URL=sqlite+aiosqlite:///./e2e_test.db ADMIN_TOKEN=test-admin-token MODEL_RUNTIME_MOCK_ENABLED=true RAG_ENABLED=true EMBEDDINGS_ENABLED=true EMBEDDINGS_BACKEND=mock MODEL_HOT_SWAP_ENABLED=true PKI_ENABLED=true REDIS_URL=redis://127.0.0.1:6379/15 ../.venv/bin/uvicorn app.main:app --port 18080 --host 127.0.0.1',
    url: 'http://127.0.0.1:18080/health',
    reuseExistingServer: !process.env.CI,
    cwd: path.resolve(__dirname, '../../control_plane'),
    timeout: 120000,
  },
});
