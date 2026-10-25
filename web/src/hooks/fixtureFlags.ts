import { useSyncExternalStore } from "react";
import { isFixtureMode } from "@/api/client";
import {
  fixtureCanUndo,
  getUndoEpoch,
  subscribeUndo,
} from "@/api/fixture";

export { isFixtureMode, fixtureCanUndo };

/** Reactive undo availability for the toolbar. */
export function useCanUndo(): boolean {
  const epoch = useSyncExternalStore(subscribeUndo, getUndoEpoch, getUndoEpoch);
  void epoch;
  return isFixtureMode() ? fixtureCanUndo() : false;
}
