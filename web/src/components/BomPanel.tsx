import type { Bom } from "@/types/contracts";

interface Props {
  bom: Bom | null | undefined;
  loading?: boolean;
}

export function BomPanel({ bom, loading }: Props) {
  if (loading) {
    return <p className="p-4 text-[13px] text-[var(--muted)]">Loading BOM…</p>;
  }
  if (!bom) {
    return (
      <div className="p-4 text-[13px] text-[var(--muted)]">
        <p className="font-medium text-[var(--ink)]">No BOM yet</p>
        <p className="mt-1">Bill of materials appears when the engine/BOM pipeline is enabled.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-[var(--border)] px-3 py-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Bill of materials</h2>
        <p className="text-[11px] text-[var(--muted)]">
          Total{" "}
          <span className="font-semibold text-[var(--ink)]">
            ${bom.total_usd.toFixed(2)}
          </span>
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead className="sticky top-0 bg-[var(--surface)]">
            <tr className="text-left text-[var(--muted)]">
              <th className="border-b border-[var(--border)] px-3 py-1.5 font-semibold">Item</th>
              <th className="border-b border-[var(--border)] px-2 py-1.5 font-semibold">Qty</th>
              <th className="border-b border-[var(--border)] px-2 py-1.5 font-semibold">Ext.</th>
            </tr>
          </thead>
          <tbody>
            {bom.lines.map((line) => (
              <tr key={line.item_key} className="align-top">
                <td className="border-b border-[var(--border)]/70 px-3 py-1.5">
                  <div className="font-medium text-[var(--ink)]">{line.description}</div>
                  <div className="font-mono text-[10px] text-[var(--muted)]">{line.item_key}</div>
                </td>
                <td className="border-b border-[var(--border)]/70 px-2 py-1.5 tabular-nums">
                  {line.quantity} {line.unit}
                </td>
                <td className="border-b border-[var(--border)]/70 px-2 py-1.5 tabular-nums">
                  {line.extended_price != null ? `$${line.extended_price.toFixed(2)}` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border-t border-[var(--border)] px-3 py-2 text-[11px] text-[var(--muted)]">
        <div className="mb-1 font-semibold text-[var(--ink)]">Assumptions</div>
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
