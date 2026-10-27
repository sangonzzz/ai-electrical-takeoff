/**
 * Bring up the isolated takeoff-e2e stack (DB takeoff_e2e), then run Playwright.
 * Never points at the default stack (:5173 / :8000 / DB takeoff).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const e2eRoot = path.join(__dirname, "..");
const repoRoot = path.join(e2eRoot, "..");
const composeFile = path.join(e2eRoot, "docker-compose.yml");
const PROJECT = "takeoff-e2e";
const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:5174";
const API_HEALTH = process.env.E2E_API_HEALTH ?? "http://localhost:8001/api/health";

const FORBIDDEN = new Set([
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:5173/",
  "http://127.0.0.1:5173/",
]);

function die(msg) {
  console.error(`[e2e] ${msg}`);
  process.exit(1);
}

function dockerCompose(args, opts = {}) {
  const cmd = ["compose", "-f", composeFile, "-p", PROJECT, ...args];
  const r = spawnSync("docker", cmd, {
    cwd: repoRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
    ...opts,
  });
  if (r.error) die(`docker compose failed: ${r.error.message}`);
  if (r.status !== 0) die(`docker compose ${args.join(" ")} exited ${r.status}`);
}

async function waitUrl(url, label, timeoutMs = 180_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) {
        console.log(`[e2e] ${label} ready (${url})`);
        return;
      }
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  die(`timed out waiting for ${label} at ${url}`);
}

function ensurePlaywrightBrowsers() {
  const r = spawnSync("npx", ["playwright", "install", "chromium"], {
    cwd: e2eRoot,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  if (r.status !== 0) die("playwright install chromium failed");
}

async function main() {
  const mode = process.argv[2] ?? "test";

  if (FORBIDDEN.has(BASE_URL.replace(/\/$/, "")) && process.env.E2E_ALLOW_DEFAULT_STACK !== "1") {
    die(
      `Refusing E2E_BASE_URL=${BASE_URL} — that is Santiago's review stack.\n` +
        `  Use the isolated stack (default http://localhost:5174) or set E2E_ALLOW_DEFAULT_STACK=1 only if you really mean it.`,
    );
  }

  if (!fs.existsSync(composeFile)) die(`missing ${composeFile}`);

  if (mode === "down") {
    dockerCompose(["down"]);
    return;
  }
  if (mode === "reset") {
    dockerCompose(["down", "-v"]);
    console.log("[e2e] volumes removed (takeoff_e2e data wiped)");
    return;
  }

  console.log(`[e2e] starting isolated stack (project=${PROJECT}, db=takeoff_e2e)`);
  // --wait blocks until healthchecks pass (Compose v2.20+)
  dockerCompose(["up", "-d", "--build", "--wait"]);

  await waitUrl(API_HEALTH, "api");
  await waitUrl(BASE_URL, "web");

  if (mode === "up") {
    console.log(`[e2e] stack up. Open ${BASE_URL} (API ${API_HEALTH})`);
    return;
  }

  ensurePlaywrightBrowsers();
  const env = { ...process.env, E2E_BASE_URL: BASE_URL };
  const test = spawnSync("npx", ["playwright", "test", ...process.argv.slice(3)], {
    cwd: e2eRoot,
    env,
    stdio: "inherit",
    shell: process.platform === "win32",
  });
  process.exit(test.status ?? 1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
