import type { ReactNode } from "react";
import { Layers, Maximize2, MousePointer2, Plus, Undo2 } from "lucide-react";
import { SUBTYPES, defaultSubtype } from "@/lib/subtypes";
import type { Category } from "@/types/contracts";
import { useUiStore, type LayerVisibility } from "@/store/uiStore";

const LAYER_KEYS: { key: keyof LayerVisibility; label: string }[] = [
  { key: "rooms", label: "Rooms" },
  { key: "detections", label: "Marks" },
  { key: "wires", label: "Wires" },
  { key: "boxes", label: "Boxes" },
];

interface Props {
  canUndo: boolean;
  onUndo: () => void;
  onFit: () => void;
}

export function FloatingToolbar({ canUndo, onUndo, onFit }: Props) {
  const mode = useUiStore((s) => s.mode);
  const setMode = useUiStore((s) => s.setMode);
  const addCategory = useUiStore((s) => s.addCategory);
  const addSubtype = useUiStore((s) => s.addSubtype);
  const setAddType = useUiStore((s) => s.setAddType);
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
        <ToolBtn disabled={!canUndo} onClick={onUndo} title="Undo (Ctrl+Z)">
          <Undo2 size={15} />
        </ToolBtn>
        <ToolBtn onClick={onFit} title="Fit (F)">
          <Maximize2 size={15} />
        </ToolBtn>
      </div>

      {mode === "add" && (
        <div className="card flex flex-wrap items-center gap-1.5 p-2 shadow-[var(--shadow-md)]">
          <select
            className="field !w-auto !py-1 !text-[12px]"
            value={addCategory}
            onChange={(e) => {
              const cat = e.target.value as Category;
              setAddType(cat, defaultSubtype(cat));
            }}
          >
            {(Object.keys(SUBTYPES) as Category[]).map((c) => (
              <option key={c} value={c}>
                {c.replace(/_/g, " ")}
              </option>
            ))}
          </select>
          <select
            className="field !w-auto !py-1 !text-[12px]"
            value={addSubtype}
            onChange={(e) => setAddType(addCategory, e.target.value)}
          >
            {(SUBTYPES[addCategory] ?? []).map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
      )}

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
