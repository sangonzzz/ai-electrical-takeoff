import { useEffect, useState, type ReactNode } from "react";
import { formatFixedDecimal, parseLocaleDecimal } from "@/lib/decimalInput";

interface Props {
  /** Visible label text (kept as a text node inside <label> for e2e). */
  label: ReactNode;
  value: number;
  digits?: number;
  className?: string;
  onCommit: (next: number) => void;
}

/**
 * Text input with decimal inputMode; displays fixed-dot decimals.
 * Commits on blur / Enter; reverts on invalid.
 */
export function DecimalField({
  label,
  value,
  digits = 1,
  className = "field font-mono",
  onCommit,
}: Props) {
  const [draft, setDraft] = useState(() => formatFixedDecimal(value, digits));

  useEffect(() => {
    setDraft(formatFixedDecimal(value, digits));
  }, [value, digits]);

  function commit() {
    const parsed = parseLocaleDecimal(draft);
    if (parsed == null) {
      setDraft(formatFixedDecimal(value, digits));
      return;
    }
    const rounded = Number(parsed.toFixed(digits));
    setDraft(formatFixedDecimal(rounded, digits));
    if (Math.abs(rounded - value) < 10 ** -(digits + 1)) return;
    onCommit(rounded);
  }

  return (
    <label className="flex flex-col gap-1">
      {typeof label === "string" ? (
        <span className="text-[11px] font-medium text-[var(--muted)]">{label}</span>
      ) : (
        label
      )}
      <input
        className={className}
        type="text"
        inputMode="decimal"
        autoComplete="off"
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.currentTarget.blur();
          }
        }}
      />
    </label>
  );
}
