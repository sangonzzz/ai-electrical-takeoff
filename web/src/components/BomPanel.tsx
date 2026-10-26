import type { Bom, BomLine } from "@/types/contracts";
import { EmptyState } from "./ui/EmptyState";

interface Props {
  bom: Bom | null | undefined;
  loading?: boolean;
}

type Section = "devices" | "boxes" | "cable" | "other";

function sectionOf(line: BomLine): Section {
  const k = line.item_key.toLowerCase();
  if (k.includes("nm_") || k.includes("cable") || line.unit === "ft") return "cable";
  if (k.includes("box") || k.includes("plate") || k.includes("gang")) return "boxes";
  if (k.includes("fan") || k.includes("light") || k.includes("switch") || k.includes("recept"))
    return "devices";
  return "other";
}

const SECTION_LABEL: Record<Section, string> = {
  devices: "Devices",
  boxes: "Boxes & plates",
  cable: "Cable",
  other: "Other",
};

export function BomPanel({ bom, loading }: Props) {
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

  const groups = (["devices", "boxes", "cable", "other"] as Section[])
    .map((s) => ({
      section: s,
      lines: bom.lines.filter((l) => sectionOf(l) === s),
    }))
    .filter((g) => g.lines.length > 0);

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Bill of materials</h2>
        <p className="text-[11px] text-[var(--muted)]">
          Total{" "}
          <span className="font-mono font-semibold text-[var(--ink)]">
            ${bom.total_usd.toFixed(2)}
          </span>
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
                      <div className="font-medium text-[var(--ink)]">{line.description}</div>
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
