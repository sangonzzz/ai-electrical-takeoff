import { useEffect, useRef, useState } from "react";
import { ChevronRight } from "lucide-react";
import type { Bom, BomLine } from "@/types/contracts";
import { formatAssumptionRows } from "@/lib/bomAssumptions";
import { formatUsd } from "@/lib/formatUsd";
import { useUiStore } from "@/store/uiStore";
import { EmptyState } from "./ui/EmptyState";

interface Props {
  bom: Bom | null | undefined;
  loading?: boolean;
}

type Section = "fixtures" | "devices" | "boxes" | "cable" | "other";

/** Mirrors engine `group_bom_lines` / Agente 8 fixture SKUs. */
function sectionOf(line: BomLine): Section {
  const k = line.item_key.toLowerCase();
  if (k.includes("nm_") || k.includes("cable") || line.unit === "ft") return "cable";
  if (k.includes("box") || k.includes("plate") || k.includes("gang")) return "boxes";
  if (
    k === "device_ceiling_fan" ||
    k === "device_exhaust_fan" ||
    k === "device_detector" ||
    k.startsWith("device_light_")
  ) {
    return "fixtures";
  }
  if (k.includes("switch") || k.includes("recept") || k.includes("junction")) return "devices";
  if (k.includes("fan") || k.includes("light") || k.includes("detector")) return "fixtures";
  return "other";
}

const SECTION_LABEL: Record<Section, string> = {
  fixtures: "Fixtures (allowance)",
  devices: "Devices",
  boxes: "Boxes & plates",
  cable: "Cable (estimated)",
  other: "Other",
};

const SUBTOTAL_ORDER: { key: Section; label: string }[] = [
  { key: "fixtures", label: "Fixtures" },
  { key: "devices", label: "Devices" },
  { key: "boxes", label: "Boxes" },
  { key: "cable", label: "Cable" },
];

function priceCaptureDate(bom: Bom): string | null {
  const raw =
    bom.assumptions?.price_capture_date ??
    bom.assumptions?.price_list_date ??
    (typeof bom.price_capture_date === "string" ? bom.price_capture_date : null) ??
    (typeof bom.price_list_date === "string" ? bom.price_list_date : null);
  if (typeof raw !== "string" || !raw.trim()) return null;
  return raw.trim();
}

/** Compact section subtotals when they reconcile with total_usd. */
function sectionSubtotals(
  lines: BomLine[],
  totalUsd: number,
): { label: string; usd: number }[] | null {
  const sums: Record<Section, number> = {
    fixtures: 0,
    devices: 0,
    boxes: 0,
    cable: 0,
    other: 0,
  };
  for (const line of lines) {
    const ext = line.extended_price;
    if (ext == null || !Number.isFinite(ext)) return null;
    sums[sectionOf(line)] += ext;
  }
  const reconcilable = sums.fixtures + sums.devices + sums.boxes + sums.cable + sums.other;
  if (Math.abs(reconcilable - totalUsd) > 0.01) return null;
  return SUBTOTAL_ORDER.filter((s) => sums[s.key] > 0.005).map((s) => ({
    label: s.label,
    usd: Math.round(sums[s.key] * 100) / 100,
  }));
}

export function BomPanel({ bom, loading }: Props) {
  const bomBaselineUsd = useUiStore((s) => s.bomBaselineUsd);
  const setBomBaselineUsd = useUiStore((s) => s.setBomBaselineUsd);
  const seeded = useRef(false);
  const [assumptionsOpen, setAssumptionsOpen] = useState(false);

  useEffect(() => {
    if (!bom || seeded.current) return;
    setBomBaselineUsd(bom.total_usd);
    seeded.current = true;
  }, [bom, setBomBaselineUsd]);

  if (loading) {
    return <p className="p-4 text-[13px] text-[var(--muted)]">Loading BOM…</p>;
  }
  if (!bom || bom.lines.length === 0) {
    return (
      <EmptyState
        title="No BOM yet"
        description="Bill of materials appears when boxes and cable runs are available for this sheet."
      />
    );
  }

  const groups = (["fixtures", "devices", "boxes", "cable", "other"] as Section[])
    .map((s) => ({
      section: s,
      lines: bom.lines.filter((l) => sectionOf(l) === s),
    }))
    .filter((g) => g.lines.length > 0);

  const delta = bomBaselineUsd != null ? bom.total_usd - bomBaselineUsd : 0;
  const showDelta = Math.abs(delta) >= 0.005;
  const assumptionRows = formatAssumptionRows(bom.assumptions ?? {});
  const captureDate = priceCaptureDate(bom);
  const subtotals = sectionSubtotals(bom.lines, bom.total_usd);
  const footnote = captureDate
    ? `Devices, boxes, cable and fixture allowances · Home Depot prices · ${captureDate}`
    : "Devices, boxes, cable and fixture allowances · Home Depot prices";

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 border-b border-[var(--border)] px-3 py-3">
        <div className="rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] p-3">
          <div className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Estimated material cost
          </div>
          <div className="mt-1 flex flex-wrap items-baseline gap-2">
            <p
              className="m-0 text-[28px] font-semibold leading-none tabular-nums tracking-tight text-[var(--ink)]"
              data-testid="bom-total"
            >
              {formatUsd(bom.total_usd)}
            </p>
            {showDelta && (
              <span
                className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                  delta > 0
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-rose-50 text-rose-700"
                }`}
                title="Change vs when this sheet was opened"
              >
                {delta > 0 ? "+" : "-"}${Math.abs(delta).toFixed(2)}
              </span>
            )}
          </div>
          <p className="mt-2 text-[11px] leading-snug text-[var(--muted)]">{footnote}</p>
          {subtotals && subtotals.length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-[var(--ink-soft)]">
              {subtotals.map((s) => (
                <li key={s.label}>
                  <span className="text-[var(--muted)]">{s.label}</span>{" "}
                  <span className="tabular-nums">{formatUsd(s.usd)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {groups.map((g) => (
          <div key={g.section}>
            <div className="sticky top-0 bg-[var(--surface-2)] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
              {SECTION_LABEL[g.section]}
            </div>
            <table className="w-full border-collapse text-[12px]">
              <tbody>
                {g.lines.map((line) => (
                  <tr key={line.item_key} className="takeoff-row align-top">
                    <td className="border-b border-[var(--border)]/70 px-3 py-1.5">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="font-medium text-[var(--ink)]">{line.description}</span>
                        {g.section === "cable" && (
                          <span
                            className="rounded bg-[var(--warn-soft)] px-1 py-px text-[9px] font-semibold uppercase tracking-wide text-[var(--warn)]"
                            title="Lengths traced from dashed plan lines. Review before quoting."
                          >
                            estimated
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-[10px] text-[var(--muted)]">
                        {line.item_key}
                      </div>
                    </td>
                    <td className="border-b border-[var(--border)]/70 px-2 py-1.5 font-mono tabular-nums">
                      {line.quantity} {line.unit}
                    </td>
                    <td className="border-b border-[var(--border)]/70 px-2 py-1.5 text-right font-mono tabular-nums">
                      {line.extended_price != null
                        ? `$${line.extended_price.toFixed(2)}`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {assumptionRows.length > 0 && (
        <div className="shrink-0 border-t border-[var(--border)] bg-[var(--surface)]">
          <button
            type="button"
            className="flex w-full items-center gap-1.5 px-3 py-2 text-left text-[12px] font-semibold text-[var(--ink)] hover:bg-[var(--surface-2)]"
            aria-expanded={assumptionsOpen}
            data-testid="bom-assumptions-toggle"
            onClick={() => setAssumptionsOpen((o) => !o)}
          >
            <ChevronRight
              size={14}
              className={`shrink-0 text-[var(--muted)] transition-transform ${
                assumptionsOpen ? "rotate-90" : ""
              }`}
            />
            Assumptions ({assumptionRows.length})
          </button>
          {assumptionsOpen && (
            <div
              className="max-h-40 overflow-y-auto border-t border-[var(--border)]/70 px-3 py-2 text-[11px] text-[var(--muted)]"
              data-testid="bom-assumptions-body"
            >
              <ul className="space-y-1.5">
                {assumptionRows.map((row) =>
                  row.kind === "metric" ? (
                    <li key={row.key} className="text-[var(--ink-soft)]">
                      {row.label}
                    </li>
                  ) : (
                    <li key={row.key} className="leading-snug text-[var(--muted)]">
                      {row.text}
                    </li>
                  ),
                )}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
