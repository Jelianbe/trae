const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: false,
  forbidOnly: false,
  retries: 0,
  workers: 1,
  reporter: 'list',
  use: {
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'msedge',
      use: {
        browserName: 'chromium',
        channel: 'msedge',
      },
    },
  ],
  webServer: {
    command: 'cd ../backend; uvicorn main:app --host 0.0.0.0 --port 8000',
    port: 8000,
    reuseExistingServer: true,
    timeout: 120000,
  },
})
