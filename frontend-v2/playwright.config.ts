import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3100",
    headless: true,
  },
  webServer: [
    {
      command:
        "python frontend-v2/tests/create_test_db.py e2e-smoke-v2.db && python -m uvicorn app.main:app --host 0.0.0.0 --port 8010",
      url: "http://localhost:8010/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      cwd: "..",
      env: {
        ...process.env,
        PYTHONPATH: "backend",
        ARIA_SCHEDULER_ENABLED: "false",
        // Hermetic E2E: never leak a developer's real cloud keys into the
        // test backend. Deterministic fallbacks keep titles, tutor replies,
        // and audio local-only stable across machines and CI. Live-provider
        // verification is a separate staging activity (see production-runbook).
        GROQ_API_KEY: "",
        ARIA_TTS_API_KEY: "",
        ARIA_STT_API_KEY: "",
        ARIA_EMBEDDING_API_KEY: "",
        DATABASE_URL: process.env.DATABASE_URL ?? "sqlite:///./e2e-smoke-v2.db",
        ARIA_CORS_ORIGINS: process.env.ARIA_CORS_ORIGINS ?? "http://localhost:3100",
        // Test-only Fernet key enabling the BYO LLM-key endpoints under E2E.
        // Never use this value outside local test runs.
        ARIA_LLM_KEYS_ENCRYPTION_KEY:
          process.env.ARIA_LLM_KEYS_ENCRYPTION_KEY ??
          "BcxusO8Zc5ehRqVpEJWCJ_zsEkhJYLh5GHtBs344Jp0=",
      },
    },
    {
      command: "npm run dev -- -p 3100",
      url: "http://localhost:3100",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8010",
        // Expose the dev-only reminder-check button under E2E.
        NEXT_PUBLIC_ENABLE_DEV_TOOLS: "1",
      },
    },
  ],
});
