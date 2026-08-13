import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
  },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --port 8000",
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        PYTHONPATH: "../backend",
        ARIA_SCHEDULER_ENABLED: "false",
        DATABASE_URL:
          process.env.DATABASE_URL ?? "sqlite:///./e2e-smoke.db",
      },
    },
    {
      command: "npm run start -- --port 3000",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
