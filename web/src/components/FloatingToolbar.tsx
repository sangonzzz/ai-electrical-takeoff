import type { ReactNode } from "react";
import { Layers, Maximize2, MousePointer2, Plus } from "lucide-react";
import { useUiStore, type LayerVisibility } from "@/store/uiStore";

const LAYER_KEYS: { key: keyof LayerVisibility; label: string }[] = [
  { key: "rooms", label: "Rooms" },
  { key: "detections", label: "Marks" },
  { key: "wires", label: "Wires" },
  { key: "boxes", label: "Boxes" },
];

interface Props {
  onFit: () => void;
}

export function FloatingToolbar({ onFit }: Props) {
  const mode = useUiStore((s) => s.mode);
  const setMode = useUiStore((s) => s.setMode);
  const layers = useUiStore((s) => s.layers);
  const toggleLayer = useUiStore((s) => s.toggleLayer);

  return (
    <div className="pointer-events-auto flex flex-col gap-2">
      <div className="card flex items-center gap-0.5 p-1 shadow-[var(--shadow-md)]">
        <ToolBtn
          active={mode === "select"}
          onClick={() => setMode("select")}
          title="Select (V)"
        >
          <MousePointer2 size={15} />
        </ToolBtn>
        <ToolBtn active={mode === "add"} onClick={() => setMode("add")} title="Add (A)">
          <Plus size={15} />
        </ToolBtn>
        <div className="mx-0.5 h-5 w-px bg-[var(--border)]" />
        <ToolBtn onClick={onFit} title="Fit (F)">
          <Maximize2 size={15} />
        </ToolBtn>
      </div>

      <div className="card p-2 shadow-[var(--shadow-md)]">
        <div className="mb-1.5 flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          <Layers size={11} /> Layers
        </div>
        <div className="flex flex-wrap gap-1">
          {LAYER_KEYS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              onClick={() => toggleLayer(key)}
              className={`rounded-md px-2 py-1 text-[11px] font-semibold transition ${
                layers[key]
                  ? "bg-[var(--ink)] text-white"
                  : "bg-[var(--surface-3)] text-[var(--muted)]"
              }`}
              aria-pressed={layers[key]}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function ToolBtn({
  children,
  active,
  disabled,
  onClick,
  title,
}: {
  children: ReactNode;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  title: string;
}) {
  return (
    <button
      type="button"
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`rounded-md p-2 transition ${
        active
          ? "bg-[var(--ink)] text-white"
          : "text-[var(--ink-soft)] hover:bg-[var(--surface-3)]"
      } disabled:opacity-40`}
    >
      {children}
    </button>
  );
}
