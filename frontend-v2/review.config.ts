import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests", testMatch: "review-fixes.spec.ts", timeout: 60_000,
  workers: 1, reporter: "list",
  use: { baseURL: process.env.ARIA_UI_BASE_URL ?? "http://localhost:3101", headless: true },
});
