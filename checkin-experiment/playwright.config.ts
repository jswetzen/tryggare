import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Check-In Station E2E tests
 *
 * These tests should work against both React and Svelte implementations
 * using data-testid attributes for element selection
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://192.168.1.164:5174',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'pnpm dev',
    url: 'http://192.168.1.164:5174',
    reuseExistingServer: true, // Use existing dev server
  },
});
