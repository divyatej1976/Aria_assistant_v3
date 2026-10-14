import { defineConfig } from "@playwright/test";

// Isolated frontend interaction checks with explicit network fixtures.
// Full integration coverage remains in playwright.config.ts.
export default defineConfig({
  testDir: "./tests",
  testMatch: "frontend-motion.spec.ts",
  timeout: 60_000,
  workers: 1,
  reporter: "list",
  use: { baseURL: process.env.ARIA_UI_BASE_URL ?? "http://localhost:3101", headless: true },
  webServer: process.env.ARIA_UI_EXTERNAL_SERVER === "1" ? undefined : {
    command: "npm run dev -- -p 3101",
    url: "http://localhost:3101/app",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: { NEXT_PUBLIC_API_URL: "http://localhost:8010" },
  },
});
