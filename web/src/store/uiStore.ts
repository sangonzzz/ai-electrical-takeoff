import { create } from "zustand";
import type { Category } from "@/types/contracts";
import { ALL_CATEGORIES } from "@/lib/colors";

export type PanelTab = "takeoff" | "details" | "bom" | "corrections";
export type InteractionMode = "select" | "add" | "wire_create";

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

export interface PaletteDrag {
  category: Category;
  subtype: string;
}

interface UiState {
  panelTab: PanelTab;
  mode: InteractionMode;
  addCategory: Category;
  addSubtype: string;
  selectedDetectionId: string | null;
  selectedWireId: string | null;
  selectedBoxId: string | null;
  /** Cable editing mode — enables wire selection / create / details. */
  editCables: boolean;
  /** First device picked while creating a new cable run. */
  wireCreateFromId: string | null;
  highlight: TakeoffHighlight | null;
  layers: LayerVisibility;
  categoryVisibility: CategoryVisibility;
  shortcutsOpen: boolean;
  /** Active palette drag (ghost preview + drop target). */
  paletteDrag: PaletteDrag | null;
  /** Last BOM total for delta badge after edits. */
  bomBaselineUsd: number | null;
  setPanelTab: (tab: PanelTab) => void;
  setMode: (mode: InteractionMode) => void;
  setAddType: (category: Category, subtype: string) => void;
  selectDetection: (id: string | null) => void;
  selectWire: (id: string | null) => void;
  selectBox: (id: string | null) => void;
  setEditCables: (on: boolean) => void;
  setWireCreateFromId: (id: string | null) => void;
  setHighlight: (highlight: TakeoffHighlight | null) => void;
  /** Highlight devices on the plan without leaving Details (wire/box from/to). */
  highlightDevices: (ids: string[]) => void;
  toggleLayer: (layer: keyof LayerVisibility) => void;
  toggleCategory: (category: Category) => void;
  setAllCategories: (on: boolean) => void;
  setShortcutsOpen: (open: boolean) => void;
  toggleShortcuts: () => void;
  setPaletteDrag: (drag: PaletteDrag | null) => void;
  setBomBaselineUsd: (n: number | null) => void;
}

export const useUiStore = create<UiState>((set) => ({
  panelTab: "takeoff",
  mode: "select",
  addCategory: "light",
  addSubtype: "recessed",
  selectedDetectionId: null,
  selectedWireId: null,
  selectedBoxId: null,
  editCables: false,
  wireCreateFromId: null,
  highlight: null,
  layers: {
    rooms: true,
    detections: true,
    wires: false, // beta — dashed-line traces; review before quoting
    boxes: false, // off by default — clutter; toggle when reviewing gangs
  },
  categoryVisibility: allCategoriesOn(),
  shortcutsOpen: false,
  paletteDrag: null,
  bomBaselineUsd: null,
  setPanelTab: (panelTab) => set({ panelTab }),
  setMode: (mode) => set({ mode }),
  setAddType: (addCategory, addSubtype) => set({ addCategory, addSubtype, mode: "add" }),
  selectDetection: (selectedDetectionId) =>
    set((s) => ({
      selectedDetectionId,
      selectedWireId: selectedDetectionId ? null : s.selectedWireId,
      selectedBoxId: selectedDetectionId ? null : s.selectedBoxId,
      panelTab: selectedDetectionId ? "details" : s.panelTab,
      highlight: null,
    })),
  selectWire: (selectedWireId) =>
    set((s) => ({
      selectedWireId,
      selectedDetectionId: selectedWireId ? null : s.selectedDetectionId,
      selectedBoxId: null,
      panelTab: selectedWireId ? "details" : s.panelTab,
      highlight: null,
    })),
  selectBox: (selectedBoxId) =>
    set((s) => ({
      selectedBoxId,
      selectedWireId: null,
      selectedDetectionId: null,
      highlight: selectedBoxId
        ? null
        : s.highlight,
      panelTab: selectedBoxId ? "details" : s.panelTab,
    })),
  setEditCables: (editCables) =>
    set((s) => ({
      editCables,
      layers: editCables ? { ...s.layers, wires: true } : s.layers,
      mode: editCables ? s.mode : "select",
      wireCreateFromId: editCables ? s.wireCreateFromId : null,
      selectedWireId: editCables ? s.selectedWireId : null,
    })),
  setWireCreateFromId: (wireCreateFromId) => set({ wireCreateFromId }),
  setHighlight: (highlight) =>
    set({
      highlight,
      selectedDetectionId: null,
      selectedWireId: null,
      selectedBoxId: null,
      panelTab: "takeoff",
    }),
  highlightDevices: (ids) =>
    set({
      highlight: {
        detectionIds: ids,
        key: `devices:${ids.join(",")}`,
        roomId: null,
      },
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
  setShortcutsOpen: (shortcutsOpen) => set({ shortcutsOpen }),
  toggleShortcuts: () => set((s) => ({ shortcutsOpen: !s.shortcutsOpen })),
  setPaletteDrag: (paletteDrag) => set({ paletteDrag }),
  setBomBaselineUsd: (bomBaselineUsd) => set({ bomBaselineUsd }),
}));
