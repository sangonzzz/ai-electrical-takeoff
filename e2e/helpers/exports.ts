/**
 * Save Playwright downloads and validate Excel/PDF with the repo venv
 * (openpyxl + pymupdf) — same stack the backend tests use.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Download, Page } from "@playwright/test";

const e2eRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.join(e2eRoot, "..");
export const DOWNLOADS_DIR = path.join(e2eRoot, "results", "downloads");

const EXPECTED_XLSX_SHEETS = [
  "Takeoff by room",
  "Detections",
  "BOM",
  "Wires",
  "Assumptions",
  "Corrections log",
];

function pythonBin(): string {
  const win = path.join(repoRoot, ".venv", "Scripts", "python.exe");
  const unix = path.join(repoRoot, ".venv", "bin", "python");
  if (fs.existsSync(win)) return win;
  if (fs.existsSync(unix)) return unix;
  return "python";
}

export function ensureDownloadsDir(): void {
  fs.mkdirSync(DOWNLOADS_DIR, { recursive: true });
}

export async function clickAndSaveDownload(
  page: Page,
  buttonName: string | RegExp,
  destName: string,
): Promise<string> {
  ensureDownloadsDir();
  const dest = path.join(DOWNLOADS_DIR, destName);
  const [download] = await Promise.all([
    page.waitForEvent("download", { timeout: 60_000 }),
    page.getByRole("button", { name: buttonName }).click(),
  ]);
  await download.saveAs(dest);
  return dest;
}

export function validateXlsx(filePath: string): string[] {
  const script = `
from openpyxl import load_workbook
import json, sys
path = sys.argv[1]
need = set(json.loads(sys.argv[2]))
wb = load_workbook(path, read_only=True, data_only=True)
names = list(wb.sheetnames)
missing = sorted(need - set(names))
if missing:
    raise SystemExit("xlsx missing sheets: " + ", ".join(missing) + " (got: " + ", ".join(names) + ")")
if wb[names[0]].max_row is not None and wb[names[0]].max_row < 1:
    raise SystemExit("xlsx first sheet has no rows")
print(",".join(names))
`;
  const out = execFileSync(
    pythonBin(),
    ["-c", script, filePath, JSON.stringify(EXPECTED_XLSX_SHEETS)],
    { encoding: "utf-8", cwd: repoRoot },
  ).trim();
  return out.split(",").filter(Boolean);
}

export function validatePdf(filePath: string): number {
  const script = `
import pymupdf, sys
path = sys.argv[1]
doc = pymupdf.open(path)
if doc.page_count < 1:
    raise SystemExit("pdf has 0 pages")
# Readable content check — quote should not be an empty shell.
text_len = sum(len(page.get_text() or "") for page in doc)
if text_len < 20:
    raise SystemExit(f"pdf has {doc.page_count} page(s) but almost no text ({text_len} chars)")
print(doc.page_count)
`;
  const out = execFileSync(pythonBin(), ["-c", script, filePath], {
    encoding: "utf-8",
    cwd: repoRoot,
  }).trim();
  return Number.parseInt(out, 10);
}

/** Inspect a Download without saving (for error messages). */
export async function downloadMeta(download: Download): Promise<string> {
  return `${download.suggestedFilename()} (${download.url()})`;
}
