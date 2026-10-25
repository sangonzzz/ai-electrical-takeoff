import { create } from "zustand";
import type { Category } from "@/types/contracts";

export type PanelTab = "takeoff" | "details" | "bom" | "corrections";
export type InteractionMode = "select" | "add";

export interface LayerVisibility {
  rooms: boolean;
  detections: boolean;
  wires: boolean;
  boxes: boolean;
}

export interface TakeoffHighlight {
  /** Detection ids that belong to the clicked takeoff cell. */
  detectionIds: string[];
  /** For UI feedback: which cell is active. */
  key: string;
  roomId: string | null;
}

interface UiState {
  panelTab: PanelTab;
  mode: InteractionMode;
  addCategory: Category;
  addSubtype: string;
  selectedDetectionId: string | null;
  highlight: TakeoffHighlight | null;
  layers: LayerVisibility;
  setPanelTab: (tab: PanelTab) => void;
  setMode: (mode: InteractionMode) => void;
  setAddType: (category: Category, subtype: string) => void;
  selectDetection: (id: string | null) => void;
  setHighlight: (highlight: TakeoffHighlight | null) => void;
  toggleLayer: (layer: keyof LayerVisibility) => void;
}

export const useUiStore = create<UiState>((set) => ({
  panelTab: "takeoff",
  mode: "select",
  addCategory: "light",
  addSubtype: "recessed",
  selectedDetectionId: null,
  highlight: null,
  layers: {
    rooms: true,
    detections: true,
    wires: true,
    boxes: true,
  },
  setPanelTab: (panelTab) => set({ panelTab }),
  setMode: (mode) => set({ mode }),
  setAddType: (addCategory, addSubtype) => set({ addCategory, addSubtype, mode: "add" }),
  selectDetection: (selectedDetectionId) =>
    set((s) => ({
      selectedDetectionId,
      panelTab: selectedDetectionId ? "details" : s.panelTab,
      highlight: null,
    })),
  setHighlight: (highlight) =>
    set({
      highlight,
      selectedDetectionId: null,
      panelTab: "takeoff",
    }),
  toggleLayer: (layer) =>
    set((s) => ({
      layers: { ...s.layers, [layer]: !s.layers[layer] },
    })),
}));
