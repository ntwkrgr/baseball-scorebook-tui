import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  use: {
    baseURL: 'http://127.0.0.1:8011',
    trace: 'on-first-retry',
  },
  webServer: {
    command: 'uv run python -m baseball_scorebook --no-browser --port 8011',
    cwd: '..',
    url: 'http://127.0.0.1:8011/api/health',
    reuseExistingServer: true,
    timeout: 120000,
  },
})
