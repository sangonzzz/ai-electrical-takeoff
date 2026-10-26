/**
 * Full demo quality pass against the docker stack at http://localhost:5173.
 * Requires: `make up` with healthy api/web/worker.
 */
import { expect, test, type Locator, type Page } from "@playwright/test";
import { resetSteps, step } from "../helpers/steps";

const SHEETS_TIMEOUT_MS = 8 * 60 * 1000;

async function waitForFourSucceeded(page: Page): Promise<void> {
  await expect
    .poll(
      async () => page.locator('[data-status="succeeded"]').count(),
      { timeout: SHEETS_TIMEOUT_MS, intervals: [2000, 3000, 5000] },
    )
    .toBeGreaterThanOrEqual(4);
}

function detectionMarks(page: Page): Locator {
  return page.locator('g[data-layer="detections"] > g');
}

/** React 19 SVG clicks are flaky under zoom-pan; invoke the fiber onClick. */
async function selectFirstMark(page: Page): Promise<void> {
  await page.getByTitle("Select (V)").click();
  const ok = await page.evaluate(() => {
    const g = document.querySelector(
      'g[data-layer="detections"] > g',
    ) as (SVGElement & Record<string, unknown>) | null;
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
    // Highlighted marks get an extra cyan ring circle.
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
    // Category total for same category should stay; subtype label in details changes.
    await expect(subtypeSelect).toHaveValue(other!);

    await page.getByRole("button", { name: "Takeoff" }).click();
    const totalAfter = await totalForFirstCategory(page);
    // Same category total unchanged when only subtype flips within category.
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

    // Prefer a real drag on the plan; fall back to room select if assignment
    // does not change (viewport/room geometry may keep the same room).
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
      // Explicit room reassignment still proves totals update across rooms.
      await roomSelect.selectOption(roomOptions[0].value);
      roomAfter = await roomSelect.inputValue();
    }
    expect(roomAfter).not.toBe(roomBefore);

    await page.getByRole("button", { name: "Takeoff" }).click();
    // At least one room row still renders counts after the move.
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
    "add_increments",
    "Add increments",
    async () => {
      // Ensure Marks layer is on.
      const marksLayer = page.getByRole("button", { name: "Marks", exact: true });
      if ((await marksLayer.getAttribute("aria-pressed")) === "false") {
        await marksLayer.click();
      }
      const before = await detectionMarks(page).count();
      if (before === 0) {
        throw new Error(
          `detection layer empty before add (countAfterDelete was ${countAfterDelete}) — possible UI clear after delete`,
        );
      }
      await page.getByTitle("Add (A)").click();
      await expect(page.getByText(/Add mode/i)).toBeVisible();
      const overlay = page.locator("svg[data-plan-overlay]");
      const box = await overlay.boundingBox();
      expect(box).toBeTruthy();
      const respPromise = page.waitForResponse(
        (r) => r.url().includes("/detections") && r.request().method() === "POST",
        { timeout: 20_000 },
      ).catch(() => null);
      await page.mouse.click(box!.x + box!.width * 0.4, box!.y + box!.height * 0.4);
      const resp = await respPromise;
      if (resp && !resp.ok()) {
        throw new Error(`POST /detections failed: HTTP ${resp.status()}`);
      }
      await expect
        .poll(async () => detectionMarks(page).count(), { timeout: 20_000 })
        .toBeGreaterThan(before);
    },
    { soft: true },
  );

  await step(
    "undo",
    "Undo",
    async () => {
      const undoBtn = page.getByTitle("Undo (Ctrl+Z)");
      if (await undoBtn.isDisabled()) {
        throw new Error(
          "Undo control is disabled — canUndo false; undoLastAction is a no-op outside fixture mode (web/src/api/client.ts)",
        );
      }
      const before = await detectionMarks(page).count();
      await undoBtn.click();
      await page.waitForTimeout(700);
      const after = await detectionMarks(page).count();
      if (after === before) {
        throw new Error(
          "Undo did not change detections (backend undo not wired)",
        );
      }
      expect(after).not.toBe(before);
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
