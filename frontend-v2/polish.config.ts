import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  testMatch: ["frontend-polish.spec.ts", "frontend-motion.spec.ts", "review-fixes.spec.ts"],
  timeout: 60_000,
  workers: 1,
  reporter: "list",
  use: { baseURL: process.env.ARIA_UI_BASE_URL ?? "http://localhost:3130", headless: true },
});
