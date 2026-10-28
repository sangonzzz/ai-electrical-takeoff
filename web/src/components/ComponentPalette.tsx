import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  AlarmSmoke,
  Box,
  Fan,
  Lightbulb,
  Plug,
  Search,
  ToggleLeft,
  Wind,
  X,
} from "lucide-react";
import { CATEGORY_COLORS, CATEGORY_LABEL } from "@/lib/colors";
import { PALETTE_MIME, paletteItems, type PaletteItem } from "@/lib/palette";
import { filterPaletteItems } from "@/lib/paletteSearch";
import type { Category } from "@/types/contracts";
import { useUiStore } from "@/store/uiStore";

const ICONS: Record<Category, ReactNode> = {
  ceiling_fan: <Fan size={14} />,
  light: <Lightbulb size={14} />,
  switch: <ToggleLeft size={14} />,
  receptacle: <Plug size={14} />,
  exhaust_fan: <Wind size={14} />,
  detector: <AlarmSmoke size={14} />,
  junction_box: <Box size={14} />,
};

/** Transparent 1×1 gif so the browser drag image does not cover our ghost. */
const EMPTY_DRAG_IMG =
  "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

const CATEGORY_ORDER: Category[] = [
  "ceiling_fan",
  "light",
  "switch",
  "receptacle",
  "exhaust_fan",
  "detector",
  "junction_box",
];

export function ComponentPalette() {
  const setAddType = useUiStore((s) => s.setAddType);
  const setPaletteDrag = useUiStore((s) => s.setPaletteDrag);
  const addCategory = useUiStore((s) => s.addCategory);
  const addSubtype = useUiStore((s) => s.addSubtype);
  const items = paletteItems();
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => filterPaletteItems(items, query), [items, query]);

  const byCategory = CATEGORY_ORDER.map((category) => ({
    category,
    items: filtered.filter((i) => i.category === category),
  })).filter((g) => g.items.length > 0);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement)?.tagName;
      const typing =
        tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" ||
        (e.target as HTMLElement)?.isContentEditable;
      if (e.key === "/" && !typing && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault();
        searchRef.current?.focus();
        searchRef.current?.select();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function clearSearch() {
    setQuery("");
    searchRef.current?.blur();
  }

  function armFirstMatch() {
    const first = filtered[0];
    if (!first) return;
    setAddType(first.category, first.subtype);
  }

  return (
    <aside className="card flex h-full min-h-0 w-[200px] shrink-0 flex-col overflow-hidden shadow-[var(--shadow-sm)]">
      <div className="border-b border-[var(--border)] px-2.5 py-2">
        <h2 className="text-[11px] font-semibold uppercase tracking-wide text-[var(--muted)]">
          Components
        </h2>
        <p className="mt-0.5 text-[11px] leading-snug text-[var(--muted)]">
          Drag onto the plan or select and click
        </p>
        <div className="relative mt-2">
          <Search
            size={13}
            className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[var(--muted)]"
            aria-hidden
          />
          <input
            ref={searchRef}
            type="text"
            inputMode="search"
            data-testid="palette-search"
            className="field w-full !py-1.5 !pl-7 !pr-7 text-[12px]"
            placeholder="Search components"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                e.preventDefault();
                clearSearch();
              }
              if (e.key === "Enter") {
                e.preventDefault();
                armFirstMatch();
              }
            }}
            aria-label="Search components"
          />
          {query.length > 0 && (
            <button
              type="button"
              className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-[var(--muted)] hover:bg-[var(--surface-3)] hover:text-[var(--ink)]"
              aria-label="Clear search"
              onClick={() => {
                setQuery("");
                searchRef.current?.focus();
              }}
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto px-1.5 py-1.5">
        {byCategory.length === 0 ? (
          <p className="px-1.5 py-3 text-[12px] leading-snug text-[var(--muted)]">
            No components match &ldquo;{query.trim()}&rdquo;.
          </p>
        ) : (
          byCategory.map(({ category, items: group }) => (
            <div key={category} className="mb-2">
              <div
                className="mb-1 flex items-center gap-1.5 px-1 text-[10px] font-semibold uppercase tracking-wide"
                style={{ color: CATEGORY_COLORS[category] }}
              >
                {ICONS[category]}
                {CATEGORY_LABEL[category]}
              </div>
              <ul className="flex flex-col gap-0.5">
                {group.map((item) => (
                  <PaletteRow
                    key={`${item.category}:${item.subtype}`}
                    item={item}
                    active={addCategory === item.category && addSubtype === item.subtype}
                    onSelect={() => setAddType(item.category, item.subtype)}
                    onDragBegin={() => setPaletteDrag(item)}
                    onDragEnd={() => setPaletteDrag(null)}
                  />
                ))}
              </ul>
            </div>
          ))
        )}
      </div>
    </aside>
  );
}

function PaletteRow({
  item,
  active,
  onSelect,
  onDragBegin,
  onDragEnd,
}: {
  item: PaletteItem;
  active: boolean;
  onSelect: () => void;
  onDragBegin: () => void;
  onDragEnd: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        draggable
        onClick={onSelect}
        onDragStart={(e) => {
          e.dataTransfer.setData(
            PALETTE_MIME,
            JSON.stringify({ category: item.category, subtype: item.subtype }),
          );
          e.dataTransfer.effectAllowed = "copy";
          const img = new Image();
          img.src = EMPTY_DRAG_IMG;
          e.dataTransfer.setDragImage(img, 0, 0);
          onDragBegin();
        }}
        onDragEnd={onDragEnd}
        className={`flex w-full items-center gap-1.5 rounded-md px-1.5 py-1 text-left text-[11px] transition ${
          active
            ? "bg-[var(--ink)] text-white"
            : "text-[var(--ink-soft)] hover:bg-[var(--surface-3)]"
        }`}
        title={`Drag to place · ${item.label}`}
      >
        <span
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-white"
          style={{ background: CATEGORY_COLORS[item.category] }}
          aria-hidden
        >
          {ICONS[item.category]}
        </span>
        <span className="truncate capitalize">{item.label}</span>
      </button>
    </li>
  );
}
