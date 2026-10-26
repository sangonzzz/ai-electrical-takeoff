import { useSyncExternalStore } from "react";
import { isFixtureMode } from "@/api/client";
import {
  fixtureCanRedo,
  fixtureCanUndo,
  getUndoEpoch,
  subscribeUndo,
} from "@/api/fixture";

export { isFixtureMode, fixtureCanUndo, fixtureCanRedo };

/** Reactive undo availability for the toolbar / header. */
export function useCanUndo(): boolean {
  const epoch = useSyncExternalStore(subscribeUndo, getUndoEpoch, getUndoEpoch);
  void epoch;
  return isFixtureMode() ? fixtureCanUndo() : false;
}

/** Reactive redo availability for the toolbar / header. */
export function useCanRedo(): boolean {
  const epoch = useSyncExternalStore(subscribeUndo, getUndoEpoch, getUndoEpoch);
  void epoch;
  return isFixtureMode() ? fixtureCanRedo() : false;
}
