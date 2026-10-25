import type { CorrectionEvent } from "@/api/types";
import type { Bom, Detection, Room } from "@/types/contracts";
import { useUiStore, type PanelTab } from "@/store/uiStore";
import { BomPanel } from "./BomPanel";
import { CorrectionsPanel } from "./CorrectionsPanel";
import { DetailsPanel } from "./DetailsPanel";
import { TakeoffPanel } from "./TakeoffPanel";

const TABS: { id: PanelTab; label: string }[] = [
  { id: "takeoff", label: "Takeoff" },
  { id: "details", label: "Details" },
  { id: "bom", label: "BOM" },
  { id: "corrections", label: "Log" },
];

interface Props {
  rooms: Room[];
  detections: Detection[];
  selected: Detection | null;
  bom: Bom | null | undefined;
  corrections: CorrectionEvent[];
  onPatch: (patch: Partial<Detection>) => void;
  onDelete: () => void;
}

export function RightPanel({
  rooms,
  detections,
  selected,
  bom,
  corrections,
  onPatch,
  onDelete,
}: Props) {
  const panelTab = useUiStore((s) => s.panelTab);
  const setPanelTab = useUiStore((s) => s.setPanelTab);

  return (
    <aside className="flex h-full min-h-0 flex-col overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface)]">
      <nav className="flex border-b border-[var(--border)]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setPanelTab(tab.id)}
            className={`flex-1 px-2 py-2 text-[12px] font-semibold ${
              panelTab === tab.id
                ? "border-b-2 border-[var(--ink)] text-[var(--ink)]"
                : "text-[var(--muted)] hover:text-[var(--ink)]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <div className="min-h-0 flex-1">
        {panelTab === "takeoff" && (
          <TakeoffPanel rooms={rooms} detections={detections} />
        )}
        {panelTab === "details" && (
          <DetailsPanel
            detection={selected}
            rooms={rooms}
            onChange={onPatch}
            onDelete={onDelete}
          />
        )}
        {panelTab === "bom" && <BomPanel bom={bom} />}
        {panelTab === "corrections" && <CorrectionsPanel corrections={corrections} />}
      </div>
    </aside>
  );
}
