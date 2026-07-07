import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: true,
  forbidOnly: !!process.env["CI"],
  retries: process.env["CI"] ? 1 : 0,
  reporter: process.env["CI"] ? [["html"], ["github"]] : [["list"]],

  projects: [
    // -------------------------------------------------------------------------
    // Unit project: local fixture-based tests — no network, no extension build.
    // Tests scraper parsing, sanitizer logic, and injector behaviour against
    // static HTML fixtures. Run with: npx playwright test --project=unit
    // -------------------------------------------------------------------------
    {
      name: "unit",
      testDir: "./tests/unit",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chromium",
      },
    },

    // -------------------------------------------------------------------------
    // Smoke project: live E2E tests against real LLM interfaces.
    // Run on a 6h GHA cron schedule (NFR-003).
    // Run with: npx playwright test --project=smoke
    // -------------------------------------------------------------------------
    {
      name: "smoke",
      testDir: "./tests/smoke",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chromium",
      },
    },
  ],
});
