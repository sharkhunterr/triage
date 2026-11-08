import { defineConfig, devices } from '@playwright/test'

// End-to-end runs against a backend started with fake services (`triage serve --demo`),
// at a phone width and a desktop width (Constitution IX).
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  use: {
    baseURL: process.env.TRIAGE_URL ?? 'http://127.0.0.1:9393',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 360, height: 780 } } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } } },
  ],
})
