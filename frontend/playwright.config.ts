import { defineConfig, devices } from '@playwright/test'

// End-to-end runs against Triage in demo mode (in-memory Radarr/TMDB library). Each project gets
// a fresh server and database: run them one after the other (`npm run e2e`). The journey runs
// at a phone width and a desktop width (Constitution IX).
const port = Number(process.env.TRIAGE_E2E_PORT ?? 9494)
const executablePath = process.env.PW_CHROMIUM_PATH || undefined

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'list' : 'line',
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    trace: 'retain-on-failure',
    launchOptions: { executablePath },
  },
  webServer: {
    command: `rm -rf .e2e-data && cd ../backend && TRIAGE_DEMO=1 TRIAGE_DATA_DIR=../frontend/.e2e-data TRIAGE_STATIC_DIR=../frontend/dist TRIAGE_PORT=${port} TRIAGE_HOST=127.0.0.1 TRIAGE_LOG_LEVEL=WARNING uv run triage serve`,
    url: `http://127.0.0.1:${port}/healthz`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
  projects: [
    { name: 'mobile', use: { ...devices['Pixel 7'], viewport: { width: 360, height: 780 } } },
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } } },
  ],
})
