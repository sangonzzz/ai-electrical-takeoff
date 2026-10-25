import { useUiStore, type LayerVisibility } from "@/store/uiStore";

const LABELS: { key: keyof LayerVisibility; label: string }[] = [
  { key: "rooms", label: "Rooms" },
  { key: "detections", label: "Detections" },
  { key: "wires", label: "Wires" },
  { key: "boxes", label: "Boxes" },
];

export function LayerToggles() {
  const layers = useUiStore((s) => s.layers);
  const toggleLayer = useUiStore((s) => s.toggleLayer);

  return (
    <div className="flex flex-wrap items-center gap-1">
      {LABELS.map(({ key, label }) => {
        const on = layers[key];
        return (
          <button
            key={key}
            type="button"
            onClick={() => toggleLayer(key)}
            className={`rounded px-2 py-1 text-[12px] font-medium transition ${
              on
                ? "bg-[var(--ink)] text-white"
                : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--ink)]"
            }`}
            aria-pressed={on}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
