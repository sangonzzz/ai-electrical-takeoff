import { defineConfig, devices } from "@playwright/test";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  testDir: path.join(root, "tests"),
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  timeout: 10 * 60 * 1000,
  expect: { timeout: 30_000 },
  reporter: [
    ["list"],
    ["json", { outputFile: path.join(root, "results", "report.json") }],
    ["html", { open: "never", outputFolder: path.join(root, "results", "html") }],
  ],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 30_000,
  },
  outputDir: path.join(root, "results", "artifacts"),
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
