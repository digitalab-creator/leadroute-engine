import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, devices } from "@playwright/test";

const frontendDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(frontendDir, "..");
const e2ePort = process.env.E2E_PORT ?? "8765";
const e2eOrigin = `http://127.0.0.1:${e2ePort}`;

function e2eServerCommand(): string {
  const args = `-m uvicorn app.main:app --app-dir backend --port ${e2ePort}`;
  const venvWin = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  const venvUnix = path.join(repoRoot, ".venv", "bin", "python");
  if (process.platform === "win32" && existsSync(venvWin)) {
    return `"${venvWin}" ${args}`;
  }
  if (existsSync(venvUnix)) {
    return `"${venvUnix}" ${args}`;
  }
  return `python ${args}`;
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: e2eOrigin,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: e2eServerCommand(),
    cwd: repoRoot,
    env: {
      PYTHONPATH: "backend",
      GEMINI_API_KEY: "",
      LEADROUTE_DB_PATH:
        process.env.LEADROUTE_DB_PATH ?? path.join(repoRoot, "var", "e2e-playwright.sqlite"),
    },
    url: `${e2eOrigin}/health`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
