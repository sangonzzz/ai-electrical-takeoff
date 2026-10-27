import { useUiStore, type LayerVisibility } from "@/store/uiStore";

const WIRES_TOOLTIP =
  "Cable runs are traced from the dashed plan lines; known limit: some cabinet/millwork lines are traced. Review before quoting.";

const LABELS: {
  key: keyof LayerVisibility;
  label: string;
  beta?: boolean;
  title?: string;
}[] = [
  { key: "rooms", label: "Rooms" },
  { key: "detections", label: "Detections" },
  { key: "wires", label: "Wires", beta: true, title: WIRES_TOOLTIP },
  { key: "boxes", label: "Boxes" },
];

export function LayerToggles() {
  const layers = useUiStore((s) => s.layers);
  const toggleLayer = useUiStore((s) => s.toggleLayer);

  return (
    <div className="flex flex-wrap items-center gap-1">
      {LABELS.map(({ key, label, beta, title }) => {
        const on = layers[key];
        return (
          <button
            key={key}
            type="button"
            onClick={() => toggleLayer(key)}
            title={title}
            className={`inline-flex items-center gap-1 rounded px-2 py-1 text-[12px] font-medium transition ${
              on
                ? "bg-[var(--ink)] text-white"
                : "bg-[var(--surface-2)] text-[var(--muted)] hover:text-[var(--ink)]"
            }`}
            aria-pressed={on}
          >
            {label}
            {beta && (
              <span
                className={`rounded px-1 py-px text-[8px] font-bold uppercase tracking-wide ${
                  on ? "bg-white/20 text-white" : "bg-[var(--warn-soft)] text-[var(--warn)]"
                }`}
              >
                beta
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
