import { create } from "zustand";
import type { Category } from "@/types/contracts";
import { ALL_CATEGORIES } from "@/lib/colors";

export type PanelTab = "takeoff" | "details" | "bom" | "corrections";
export type InteractionMode = "select" | "add";

export interface LayerVisibility {
  rooms: boolean;
  detections: boolean;
  wires: boolean;
  boxes: boolean;
}

export type CategoryVisibility = Record<Category, boolean>;

export interface TakeoffHighlight {
  /** Detection ids that belong to the clicked takeoff cell. */
  detectionIds: string[];
  /** For UI feedback: which cell is active. */
  key: string;
  roomId: string | null;
}

function allCategoriesOn(): CategoryVisibility {
  return Object.fromEntries(ALL_CATEGORIES.map((c) => [c, true])) as CategoryVisibility;
}

interface UiState {
  panelTab: PanelTab;
  mode: InteractionMode;
  addCategory: Category;
  addSubtype: string;
  selectedDetectionId: string | null;
  highlight: TakeoffHighlight | null;
  layers: LayerVisibility;
  categoryVisibility: CategoryVisibility;
  setPanelTab: (tab: PanelTab) => void;
  setMode: (mode: InteractionMode) => void;
  setAddType: (category: Category, subtype: string) => void;
  selectDetection: (id: string | null) => void;
  setHighlight: (highlight: TakeoffHighlight | null) => void;
  toggleLayer: (layer: keyof LayerVisibility) => void;
  toggleCategory: (category: Category) => void;
  setAllCategories: (on: boolean) => void;
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
    boxes: false, // off by default — clutter; toggle when reviewing gangs
  },
  categoryVisibility: allCategoriesOn(),
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
  toggleCategory: (category) =>
    set((s) => ({
      categoryVisibility: {
        ...s.categoryVisibility,
        [category]: !s.categoryVisibility[category],
      },
    })),
  setAllCategories: (on) =>
    set({
      categoryVisibility: Object.fromEntries(
        ALL_CATEGORIES.map((c) => [c, on]),
      ) as CategoryVisibility,
    }),
}));
