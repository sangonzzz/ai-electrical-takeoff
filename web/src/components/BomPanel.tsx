import { useEffect, useRef } from "react";
import type { Bom, BomLine } from "@/types/contracts";
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

export function BomPanel({ bom, loading }: Props) {
  const bomBaselineUsd = useUiStore((s) => s.bomBaselineUsd);
  const setBomBaselineUsd = useUiStore((s) => s.setBomBaselineUsd);
  const seeded = useRef(false);

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

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Bill of materials</h2>
        <p className="flex flex-wrap items-center gap-2 text-[11px] text-[var(--muted)]">
          <span>
            Total{" "}
            <span className="font-mono font-semibold text-[var(--ink)]">
              ${bom.total_usd.toFixed(2)}
            </span>
          </span>
          {showDelta && (
            <span
              className={`rounded-md px-1.5 py-0.5 font-mono text-[10px] font-bold ${
                delta > 0
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-rose-50 text-rose-700"
              }`}
              title="Change vs when this sheet was opened"
            >
              {delta > 0 ? "+" : ""}${delta.toFixed(2)}
            </span>
          )}
        </p>
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
                            title="Lengths traced from dashed plan lines — review before quoting"
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

      <div className="m-3 rounded-[10px] border border-[var(--border)] bg-[var(--surface-2)] p-3 text-[11px] text-[var(--muted)]">
        <div className="mb-1.5 font-semibold text-[var(--ink)]">Assumptions</div>
        <ul className="space-y-0.5">
          {Object.entries(bom.assumptions).map(([k, v]) => (
            <li key={k}>
              <span className="font-mono">{k}</span>: {String(v)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
