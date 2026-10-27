import type { CorrectionEvent, WireRunPatchBody } from "@/api/types";
import type { Bom, Box, Detection, Room, WireRun } from "@/types/contracts";
import { useUiStore, type PanelTab } from "@/store/uiStore";
import { BomPanel } from "./BomPanel";
import { BoxDetailsPanel } from "./BoxDetailsPanel";
import { CorrectionsPanel } from "./CorrectionsPanel";
import { DetailsPanel } from "./DetailsPanel";
import { TakeoffPanel } from "./TakeoffPanel";
import { WireDetailsPanel } from "./WireDetailsPanel";

const TABS: { id: PanelTab; label: string }[] = [
  { id: "takeoff", label: "Takeoff" },
  { id: "details", label: "Details" },
  { id: "bom", label: "BOM" },
  { id: "corrections", label: "Log" },
];

interface Props {
  rooms: Room[];
  detections: Detection[];
  wires?: WireRun[];
  boxes?: Box[];
  selected: Detection | null;
  selectedWire: WireRun | null;
  selectedBox: Box | null;
  bom: Bom | null | undefined;
  corrections: CorrectionEvent[];
  onPatch: (patch: Partial<Detection>) => void;
  onDelete: () => void;
  onPatchWire: (patch: WireRunPatchBody) => void;
  onDeleteWire: () => void;
  onHighlightDevices: (ids: string[]) => void;
}

export function RightPanel({
  rooms,
  detections,
  selected,
  selectedWire,
  selectedBox,
  bom,
  corrections,
  onPatch,
  onDelete,
  onPatchWire,
  onDeleteWire,
  onHighlightDevices,
}: Props) {
  const panelTab = useUiStore((s) => s.panelTab);
  const setPanelTab = useUiStore((s) => s.setPanelTab);

  return (
    <aside className="card flex h-full min-h-0 flex-col overflow-hidden">
      <nav className="flex border-b border-[var(--border)]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setPanelTab(tab.id)}
            className={`flex-1 px-2 py-2.5 text-[12px] font-semibold transition ${
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
        {panelTab === "details" &&
          (selectedWire ? (
            <WireDetailsPanel
              wire={selectedWire}
              detections={detections}
              onChange={onPatchWire}
              onDelete={onDeleteWire}
              onHighlightDevice={(id) => onHighlightDevices([id])}
            />
          ) : selectedBox ? (
            <BoxDetailsPanel
              box={selectedBox}
              detections={detections}
              onHighlightDevices={onHighlightDevices}
            />
          ) : (
            <DetailsPanel
              detection={selected}
              rooms={rooms}
              onChange={onPatch}
              onDelete={onDelete}
            />
          ))}
        {panelTab === "bom" && <BomPanel bom={bom} />}
        {panelTab === "corrections" && (
          <CorrectionsPanel corrections={corrections} />
        )}
      </div>
    </aside>
  );
}
