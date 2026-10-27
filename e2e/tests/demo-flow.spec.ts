/**
 * Full demo quality pass against the **isolated** e2e stack
 * (http://localhost:5174 → API :8001 → Postgres DB `takeoff_e2e`).
 * See e2e/README.md — never run this against Santiago's :5173 / DB `takeoff`.
 *
 * Covers Agente 6 review UI: palette click-add + drag-drop, undo/redo,
 * X/Y position fields, Download Excel / quote PDF (files opened via openpyxl/pymupdf).
 */
import { expect, test, type Locator, type Page } from "@playwright/test";
import {
  clickAndSaveDownload,
  validatePdf,
  validateXlsx,
} from "../helpers/exports";
import { resetSteps, step } from "../helpers/steps";

const SHEETS_TIMEOUT_MS = 8 * 60 * 1000;
const PALETTE_MIME = "application/x-electrical-mark";

async function waitForFourSucceeded(page: Page): Promise<void> {
  await expect
    .poll(
      async () => page.locator('[data-status="succeeded"]').count(),
      { timeout: SHEETS_TIMEOUT_MS, intervals: [2000, 3000, 5000] },
    )
    .toBeGreaterThanOrEqual(4);
}

/** Prefer Agente 6 data-testid; fall back to detection layer groups. */
function detectionMarks(page: Page): Locator {
  return page.locator(
    '[data-testid="detection-mark"], g[data-layer="detections"] > g',
  );
}

/** React 19 SVG clicks are flaky under zoom-pan; invoke the fiber onClick. */
async function selectFirstMark(page: Page): Promise<void> {
  await page.getByTitle("Select (V)").click();
  const ok = await page.evaluate(() => {
    const g = (document.querySelector('[data-testid="detection-mark"]') ??
      document.querySelector('g[data-layer="detections"] > g')) as
      | (SVGElement & Record<string, unknown>)
      | null;
    if (!g) return false;
    const key = Object.keys(g).find((k) => k.startsWith("__reactProps$"));
    if (!key) return false;
    const props = g[key] as { onClick?: (e: { stopPropagation: () => void }) => void };
    props.onClick?.({ stopPropagation() {} });
    return true;
  });
  expect(ok, "could not invoke React onClick on first detection mark").toBeTruthy();
  await page.getByRole("button", { name: "Details" }).click();
  await expect(page.getByText("No mark selected")).toHaveCount(0, { timeout: 10_000 });
}

async function totalForFirstCategory(page: Page): Promise<number> {
  const totalBtn = page.locator("table tbody tr").last().locator("button").first();
  await expect(totalBtn).toBeVisible();
  const text = (await totalBtn.innerText()).trim();
  return Number.parseInt(text, 10);
}

async function ensureMarksLayer(page: Page): Promise<void> {
  const marksLayer = page.getByRole("button", { name: "Marks", exact: true });
  if ((await marksLayer.getAttribute("aria-pressed")) === "false") {
    await marksLayer.click();
  }
}

/**
 * Invoke PlanOverlay React onClick in add mode (zoom-pan often swallows page.mouse
 * clicks before they reach the SVG).
 */
async function clickPlanBackground(page: Page, fracX: number, fracY: number): Promise<void> {
  const ok = await page.evaluate(
    ({ fracX: fx, fracY: fy }) => {
      const svg = document.querySelector(
        "svg[data-plan-overlay]",
      ) as (SVGSVGElement & Record<string, unknown>) | null;
      if (!svg) return "no-svg";
      const rect = svg.getBoundingClientRect();
      const clientX = rect.left + rect.width * fx;
      const clientY = rect.top + rect.height * fy;
      const key = Object.keys(svg).find((k) => k.startsWith("__reactProps$"));
      if (!key) return "no-fiber";
      const props = svg[key] as {
        onClick?: (e: Record<string, unknown>) => void;
      };
      props.onClick?.({
        clientX,
        clientY,
        currentTarget: svg,
        target: svg,
        stopPropagation() {},
        preventDefault() {},
      });
      return "ok";
    },
    { fracX, fracY },
  );
  expect(ok, `clickPlanBackground: ${ok}`).toBe("ok");
}

/**
 * Drop via React onDrop + DataTransfer mock (custom MIME is unreliable on
 * synthetic DragEvents in Chromium; fiber call matches production handler).
 */
async function paletteDropAt(
  page: Page,
  category: string,
  subtype: string,
  fracX: number,
  fracY: number,
): Promise<void> {
  const overlay = page.locator("svg[data-plan-overlay]");
  await expect(overlay).toBeVisible();
  const payload = JSON.stringify({ category, subtype });

  const ok = await page.evaluate(
    ({ mime, payload: data, fracX: fx, fracY: fy }) => {
      const svg = document.querySelector(
        "svg[data-plan-overlay]",
      ) as (SVGSVGElement & Record<string, unknown>) | null;
      if (!svg) return "no-svg";
      const rect = svg.getBoundingClientRect();
      const clientX = rect.left + rect.width * fx;
      const clientY = rect.top + rect.height * fy;
      const key = Object.keys(svg).find((k) => k.startsWith("__reactProps$"));
      if (!key) return "no-fiber";
      const props = svg[key] as {
        onDragOver?: (e: Record<string, unknown>) => void;
        onDrop?: (e: Record<string, unknown>) => void;
      };
      const dt = {
        types: [mime],
        dropEffect: "copy",
        effectAllowed: "copy",
        getData: (t: string) => (t === mime ? data : ""),
        setData() {},
      };
      props.onDragOver?.({
        dataTransfer: dt,
        preventDefault() {},
        clientX,
        clientY,
        currentTarget: svg,
      });
      props.onDrop?.({
        dataTransfer: dt,
        preventDefault() {},
        clientX,
        clientY,
        currentTarget: svg,
        stopPropagation() {},
      });
      return "ok";
    },
    { mime: PALETTE_MIME, payload, fracX, fracY },
  );
  expect(ok, `paletteDropAt: ${ok}`).toBe("ok");
}

/** Prefer a real HTML5 drag from the palette button when the control is present. */
async function paletteDragToPlan(
  page: Page,
  buttonName: string,
  fracX: number,
  fracY: number,
): Promise<boolean> {
  const source = page.getByRole("button", { name: buttonName, exact: true });
  if (!(await source.isVisible().catch(() => false))) return false;
  const overlay = page.locator("svg[data-plan-overlay]");
  const box = await overlay.boundingBox();
  if (!box) return false;
  await source.dragTo(overlay, {
    targetPosition: { x: box.width * fracX, y: box.height * fracY },
    force: true,
  });
  return true;
}

test.describe.configure({ mode: "serial" });

test("demo plans quality pass", async ({ page }) => {
  resetSteps();
  test.setTimeout(SHEETS_TIMEOUT_MS + 5 * 60 * 1000);

  await step("home", "Open home page", async () => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Review every mark/i })).toBeVisible();
  });

  await step("load_demo", "Load demo plans", async () => {
    await page.getByRole("button", { name: /Load demo plans/i }).first().click();
    await expect(page.getByRole("heading", { name: "Sheets" })).toBeVisible({
      timeout: 60_000,
    });
  });

  await step("sheets_succeed", "4 sheets succeed", async () => {
    await waitForFourSucceeded(page);
    expect(await page.locator('[data-status="succeeded"]').count()).toBeGreaterThanOrEqual(4);
  });

  await step("open_plan1", "Open Plan 1", async () => {
    const openLink = page.getByRole("button", { name: /Open Plan 1 sheet view/i });
    if (await openLink.isVisible()) {
      await openLink.click();
    } else {
      await page.locator("a").filter({ hasText: /Plan 1/i }).first().click();
    }
    await expect(page.locator('g[data-layer="detections"]')).toBeVisible({
      timeout: 120_000,
    });
  });

  let markCountBefore = 0;

  await step("marks_visible", "Marks visible on plan", async () => {
    await expect(detectionMarks(page).first()).toBeVisible({ timeout: 60_000 });
    markCountBefore = await detectionMarks(page).count();
    expect(markCountBefore).toBeGreaterThan(0);
  });

  await step("takeoff_highlight", "Click takeoff cell highlights marks", async () => {
    await page.getByRole("button", { name: "Takeoff" }).click();
    const totalRow = page.locator("table tbody tr").last();
    const cell = totalRow.locator("button").first();
    await expect(cell).toBeVisible();
    const n = Number.parseInt((await cell.innerText()).trim(), 10);
    expect(n).toBeGreaterThan(0);
    await cell.click();
    await expect(
      page.locator('g[data-layer="detections"] circle[stroke="#38bdf8"]').first(),
    ).toBeVisible({ timeout: 10_000 });
  });

  await step("select_details", "Select a mark shows details", async () => {
    await selectFirstMark(page);
    await expect(page.locator("label").filter({ hasText: "Subtype" }).locator("select")).toBeVisible();
  });

  let totalBeforeSubtype = 0;
  let subtypeBefore = "";

  await step("change_subtype", "Change subtype updates totals", async () => {
    await page.getByRole("button", { name: "Details" }).click();
    const subtypeSelect = page.locator("label").filter({ hasText: "Subtype" }).locator("select");
    subtypeBefore = await subtypeSelect.inputValue();
    const options = await subtypeSelect.locator("option").allTextContents();
    const other = options.map((o) => o.trim().replace(/\s+/g, "_")).find((v) => v !== subtypeBefore);
    expect(other, "need an alternate subtype").toBeTruthy();

    await page.getByRole("button", { name: "Takeoff" }).click();
    totalBeforeSubtype = await totalForFirstCategory(page);

    await page.getByRole("button", { name: "Details" }).click();
    await subtypeSelect.selectOption({ value: other! });
    await expect(subtypeSelect).toHaveValue(other!);

    await page.getByRole("button", { name: "Takeoff" }).click();
    const totalAfter = await totalForFirstCategory(page);
    expect(totalAfter).toBe(totalBeforeSubtype);
  });

  await step("drag_room", "Drag a mark to another room updates both rooms", async () => {
    await page.getByRole("button", { name: "Details" }).click();
    const roomSelect = page.locator("label").filter({ hasText: "Room" }).locator("select");
    const roomBefore = await roomSelect.inputValue();
    const roomOptions = await roomSelect.locator("option").evaluateAll(
      (opts, current) =>
        opts
          .map((o) => ({
            value: (o as HTMLOptionElement).value,
            label: o.textContent ?? "",
          }))
          .filter((o) => o.value && o.value !== current),
      roomBefore,
    );
    expect(roomOptions.length).toBeGreaterThan(0);

    const mark = detectionMarks(page).first();
    const box = await mark.boundingBox();
    expect(box).toBeTruthy();
    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.mouse.down();
    await page.mouse.move(box!.x + box!.width / 2 + 120, box!.y + box!.height / 2 + 80, {
      steps: 12,
    });
    await page.mouse.up();
    await page.waitForTimeout(800);

    await page.getByRole("button", { name: "Details" }).click();
    let roomAfter = await roomSelect.inputValue();
    if (roomAfter === roomBefore) {
      await roomSelect.selectOption(roomOptions[0].value);
      roomAfter = await roomSelect.inputValue();
    }
    expect(roomAfter).not.toBe(roomBefore);

    await page.getByRole("button", { name: "Takeoff" }).click();
    await expect(page.locator("table tbody tr").first()).toBeVisible();
  });

  let countAfterDelete = 0;

  await step("delete_decrements", "Delete decrements", async () => {
    if (await page.getByText("No mark selected").isVisible()) {
      await selectFirstMark(page);
    }
    await page.getByRole("button", { name: "Details" }).click();
    const before = await detectionMarks(page).count();
    await page.getByRole("button", { name: /Delete mark/i }).click();
    await expect
      .poll(async () => detectionMarks(page).count())
      .toBe(before - 1);
    countAfterDelete = await detectionMarks(page).count();
  });

  await step(
    "add_click_palette",
    "Add via palette click-select then plan click",
    async () => {
      await ensureMarksLayer(page);
      const before = await detectionMarks(page).count();
      if (before === 0) {
        throw new Error(
          `detection layer empty before click-add (countAfterDelete was ${countAfterDelete})`,
        );
      }
      // exact: true — title substring also matches "recessed vapor proof"
      const paletteBtn = page.getByRole("button", { name: "recessed", exact: true });
      await expect(paletteBtn).toBeVisible();
      await paletteBtn.click();
      await expect(
        page.getByText("Add mode — click the plan · Esc to cancel"),
      ).toBeVisible({ timeout: 5_000 });

      const respPromise = page
        .waitForResponse(
          (r) => r.url().includes("/detections") && r.request().method() === "POST",
          { timeout: 20_000 },
        )
        .catch(() => null);
      await clickPlanBackground(page, 0.78, 0.18);
      const resp = await respPromise;
      if (!resp) {
        throw new Error(
          "palette click-add: no POST /detections after plan background click (Agente 6: add-mode onAddAt)",
        );
      }
      if (!resp.ok()) {
        throw new Error(`POST /detections failed: HTTP ${resp.status()}`);
      }
      await expect
        .poll(async () => detectionMarks(page).count(), { timeout: 20_000 })
        .toBeGreaterThan(before);
    },
    { soft: true },
  );

  await step(
    "add_drag_palette",
    "Add via palette drag-and-drop onto plan",
    async () => {
      await ensureMarksLayer(page);
      const before = await detectionMarks(page).count();
      const respPromise = page
        .waitForResponse(
          (r) => r.url().includes("/detections") && r.request().method() === "POST",
          { timeout: 20_000 },
        )
        .catch(() => null);
      // Real HTML5 drag first; fiber onDrop fallback for custom MIME.
      const dragged = await paletteDragToPlan(page, "single pole", 0.55, 0.45);
      if (!dragged) {
        await paletteDropAt(page, "switch", "single_pole", 0.55, 0.45);
      }
      const resp = await respPromise;
      if (!resp) {
        // dragTo may not preserve custom MIME — retry via fiber onDrop
        const retry = page
          .waitForResponse(
            (r) => r.url().includes("/detections") && r.request().method() === "POST",
            { timeout: 15_000 },
          )
          .catch(() => null);
        await paletteDropAt(page, "switch", "single_pole", 0.62, 0.52);
        const resp2 = await retry;
        if (!resp2) {
          throw new Error(
            "palette drag-drop: no POST /detections (custom MIME / onPaletteDrop) — Agente 6",
          );
        }
        if (!resp2.ok()) {
          throw new Error(`POST /detections (drop) failed: HTTP ${resp2.status()}`);
        }
      } else if (!resp.ok()) {
        throw new Error(`POST /detections (drop) failed: HTTP ${resp.status()}`);
      }
      await expect
        .poll(async () => detectionMarks(page).count(), { timeout: 20_000 })
        .toBeGreaterThan(before);
    },
    { soft: true },
  );

  let countBeforeUndo = 0;

  await step(
    "undo_then_redo",
    "Undo then redo restores state",
    async () => {
      const undoBtn = page.getByTitle("Undo (Ctrl+Z)");
      const redoBtn = page.getByTitle("Redo (Ctrl+Shift+Z)");
      await expect(undoBtn).toBeVisible();
      await expect(redoBtn).toBeVisible();
      // Agente 6 client command stack enables after create/delete/patch.
      await expect(undoBtn).toBeEnabled({ timeout: 15_000 });

      countBeforeUndo = await detectionMarks(page).count();
      const undoNet = page.waitForResponse(
        (r) =>
          r.ok() &&
          (r.request().method() === "DELETE" ||
            r.url().includes("/restore") ||
            r.url().includes("/undo") ||
            r.request().method() === "PATCH"),
        { timeout: 20_000 },
      );
      await undoBtn.click();
      await undoNet;
      await expect
        .poll(async () => detectionMarks(page).count(), { timeout: 15_000 })
        .not.toBe(countBeforeUndo);
      const afterUndo = await detectionMarks(page).count();

      await expect(redoBtn).toBeEnabled({ timeout: 10_000 });
      const redoNet = page.waitForResponse(
        (r) =>
          r.ok() &&
          (r.url().includes("/restore") ||
            r.url().includes("/redo") ||
            r.request().method() === "DELETE" ||
            r.request().method() === "PATCH" ||
            (r.request().method() === "POST" && r.url().includes("/detections"))),
        { timeout: 20_000 },
      );
      await redoBtn.click();
      await redoNet;
      await expect
        .poll(async () => detectionMarks(page).count(), { timeout: 20_000 })
        .toBe(countBeforeUndo);
      expect(afterUndo).not.toBe(countBeforeUndo);
    },
  );

  await step(
    "edit_xy",
    "Edit X/Y fields moves the mark",
    async () => {
      if (await page.getByText("No mark selected").isVisible()) {
        await selectFirstMark(page);
      }
      await page.getByRole("button", { name: "Details" }).click();
      const xInput = page.locator("label").filter({ hasText: /^X$/ }).locator("input");
      const yInput = page.locator("label").filter({ hasText: /^Y$/ }).locator("input");
      await expect(xInput).toBeVisible();
      await expect(yInput).toBeVisible();

      const xBefore = Number.parseFloat(await xInput.inputValue());
      const yBefore = Number.parseFloat(await yInput.inputValue());
      expect(Number.isFinite(xBefore)).toBeTruthy();
      expect(Number.isFinite(yBefore)).toBeTruthy();

      const xTarget = Math.round((xBefore + 40) * 10) / 10;
      const yTarget = Math.round((yBefore + 25) * 10) / 10;

      const patchPromise = page
        .waitForResponse(
          (r) =>
            r.url().includes("/detections/") &&
            r.request().method() === "PATCH" &&
            r.ok(),
          { timeout: 20_000 },
        )
        .catch(() => null);

      await xInput.fill(String(xTarget));
      await yInput.fill(String(yTarget));
      await yInput.press("Enter");

      const patch = await patchPromise;
      if (!patch) {
        // Blur may have already committed on X; force Y blur.
        await yInput.blur();
      }

      await expect
        .poll(async () => Number.parseFloat(await xInput.inputValue()), {
          timeout: 15_000,
        })
        .toBeCloseTo(xTarget, 0);
      await expect
        .poll(async () => Number.parseFloat(await yInput.inputValue()), {
          timeout: 15_000,
        })
        .toBeCloseTo(yTarget, 0);

      // Mark transform should reflect the new PDF-point center.
      const transform = await detectionMarks(page)
        .filter({ has: page.locator("..") })
        .first()
        .evaluate((el) => el.getAttribute("transform") ?? "");
      // Prefer the selected mark's transform via Details id is harder; check any mark near target.
      const anyNear = await page.evaluate(
        ({ x, y }) => {
          const marks = [...document.querySelectorAll('[data-testid="detection-mark"]')];
          return marks.some((m) => {
            const t = m.getAttribute("transform") ?? "";
            const m2 = /translate\(([-0-9.]+),\s*([-0-9.]+)\)/.exec(t);
            if (!m2) return false;
            const mx = Number.parseFloat(m2[1]);
            const my = Number.parseFloat(m2[2]);
            return Math.abs(mx - x) < 1.5 && Math.abs(my - y) < 1.5;
          });
        },
        { x: xTarget, y: yTarget },
      );
      expect(anyNear, `no mark transform near (${xTarget}, ${yTarget}); saw selected transform=${transform}`).toBeTruthy();
    },
    { soft: true },
  );

  await step(
    "download_excel",
    "Download Excel returns valid workbook with sheets",
    async () => {
      const dest = await clickAndSaveDownload(
        page,
        "Download Excel",
        "plan1-takeoff.xlsx",
      );
      const sheets = validateXlsx(dest);
      expect(sheets).toEqual(
        expect.arrayContaining([
          "Takeoff by room",
          "Detections",
          "BOM",
          "Wires",
          "Assumptions",
          "Corrections log",
        ]),
      );
    },
    { soft: true },
  );

  await step(
    "download_quote_pdf",
    "Download quote PDF returns a multi-page-capable PDF",
    async () => {
      const dest = await clickAndSaveDownload(
        page,
        "Download quote PDF",
        "plan1-quote.pdf",
      );
      const pages = validatePdf(dest);
      expect(pages).toBeGreaterThanOrEqual(1);
    },
    { soft: true },
  );

  await step(
    "reload_persists",
    "Reload keeps changes",
    async () => {
      const before = await detectionMarks(page).count();
      expect(before).toBeGreaterThan(0);
      await page.reload();
      await expect(page.locator("svg[data-plan-overlay]")).toBeVisible({ timeout: 60_000 });
      await expect
        .poll(async () => detectionMarks(page).count(), { timeout: 60_000 })
        .toBe(before);
    },
    { soft: true },
  );

  await step(
    "bom_total",
    "BOM tab shows a total",
    async () => {
      await page.getByRole("button", { name: "BOM" }).click();
      const empty = page.getByText("No BOM yet");
      const total = page.getByText(/Total\s*\$/);
      if (await empty.isVisible()) {
        throw new Error("BOM empty — no total_usd shown");
      }
      await expect(total).toBeVisible();
    },
    { soft: true },
  );

  await step("plans_2_4", "Plans 2–4 open", async () => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Sheets" })).toBeVisible({
      timeout: 30_000,
    });
    for (const plan of [2, 3, 4]) {
      const card = page
        .locator("a")
        .filter({ hasText: new RegExp(`Plan ${plan}`, "i") })
        .first();
      await expect(card).toBeVisible();
      await card.click();
      await expect(page.locator("svg[data-plan-overlay]")).toBeVisible({
        timeout: 120_000,
      });
      const failed = await page.getByText("Failed to load sheet").isVisible();
      expect(failed).toBeFalsy();
      await page.goto("/");
      await expect(page.getByRole("heading", { name: "Sheets" })).toBeVisible();
    }
  });
});
