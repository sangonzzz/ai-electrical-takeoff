import { MousePointer2, Plus, Undo2 } from "lucide-react";
import { CATEGORY_LABEL } from "@/lib/colors";
import { SUBTYPES, defaultSubtype } from "@/lib/subtypes";
import type { Category } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";

interface Props {
  canUndo: boolean;
  onUndo: () => void;
}

export function Toolbar({ canUndo, onUndo }: Props) {
  const mode = useUiStore((s) => s.mode);
  const addCategory = useUiStore((s) => s.addCategory);
  const addSubtype = useUiStore((s) => s.addSubtype);
  const setMode = useUiStore((s) => s.setMode);
  const setAddType = useUiStore((s) => s.setAddType);

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex rounded-md border border-[var(--border)] bg-[var(--surface)] p-0.5">
        <button
          type="button"
          onClick={() => setMode("select")}
          className={`inline-flex items-center gap-1 rounded px-2.5 py-1.5 text-[12px] font-medium ${
            mode === "select" ? "bg-[var(--ink)] text-white" : "text-[var(--muted)]"
          }`}
        >
          <MousePointer2 size={14} /> Select
        </button>
        <button
          type="button"
          onClick={() => setMode("add")}
          className={`inline-flex items-center gap-1 rounded px-2.5 py-1.5 text-[12px] font-medium ${
            mode === "add" ? "bg-[var(--ink)] text-white" : "text-[var(--muted)]"
          }`}
        >
          <Plus size={14} /> Add
        </button>
      </div>

      {mode === "add" && (
        <div className="flex flex-wrap items-center gap-1.5">
          <select
            className="field !py-1.5 !text-[12px]"
            value={addCategory}
            onChange={(e) => {
              const cat = e.target.value as Category;
              setAddType(cat, defaultSubtype(cat));
            }}
          >
            {(Object.keys(SUBTYPES) as Category[]).map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </select>
          <select
            className="field !py-1.5 !text-[12px]"
            value={addSubtype}
            onChange={(e) => setAddType(addCategory, e.target.value)}
          >
            {(SUBTYPES[addCategory] ?? []).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      )}

      <button
        type="button"
        disabled={!canUndo}
        onClick={onUndo}
        className="inline-flex items-center gap-1 rounded border border-[var(--border)] bg-[var(--surface)] px-2.5 py-1.5 text-[12px] font-medium text-[var(--ink)] disabled:opacity-40"
      >
        <Undo2 size={14} /> Undo
      </button>
    </div>
  );
}
