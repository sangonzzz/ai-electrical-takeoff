import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const RESULTS = path.join(root, "results");
const STEPS_JSON = path.join(RESULTS, "steps.json");

export type StepStatus = "pass" | "fail" | "skip";

export interface StepRecord {
  id: string;
  title: string;
  status: StepStatus;
  detail?: string;
  ms?: number;
}

const steps: StepRecord[] = [];

export function resetSteps(): void {
  steps.length = 0;
  fs.mkdirSync(RESULTS, { recursive: true });
}

export async function step(
  id: string,
  title: string,
  fn: () => Promise<void>,
  opts: { soft?: boolean } = {},
): Promise<void> {
  const t0 = Date.now();
  try {
    await fn();
    steps.push({ id, title, status: "pass", ms: Date.now() - t0 });
  } catch (err) {
    const detail = err instanceof Error ? err.message : String(err);
    steps.push({ id, title, status: "fail", detail, ms: Date.now() - t0 });
    flushSteps();
    if (!opts.soft) throw err;
    return;
  }
  flushSteps();
}

export function markSkip(id: string, title: string, detail: string): void {
  steps.push({ id, title, status: "skip", detail });
  flushSteps();
}

export function flushSteps(): void {
  fs.mkdirSync(RESULTS, { recursive: true });
  fs.writeFileSync(STEPS_JSON, JSON.stringify({ steps }, null, 2) + "\n", "utf-8");
  const lines = [
    "# E2E step results",
    "",
    `| step | status | ms | detail |`,
    `|------|--------|---:|--------|`,
    ...steps.map(
      (s) =>
        `| ${s.id} | **${s.status}** | ${s.ms ?? ""} | ${(s.detail ?? "").replace(/\|/g, "/")} |`,
    ),
    "",
  ];
  fs.writeFileSync(path.join(RESULTS, "steps.md"), lines.join("\n"), "utf-8");
}

export function getSteps(): StepRecord[] {
  return [...steps];
}
