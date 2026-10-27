import { describe, expect, it } from "vitest";
import {
  emptyStack,
  inversePatchFrom,
  popRedo,
  popUndo,
  pushCommand,
} from "./commandStack";

describe("commandStack", () => {
  it("push clears redo and popUndo / popRedo invert each other", () => {
    let s = emptyStack();
    s = pushCommand(s, { kind: "create", detectionId: "a" });
    s = pushCommand(s, { kind: "delete", detectionId: "b" });
    expect(s.undo).toHaveLength(2);
    expect(s.redo).toHaveLength(0);

    const u = popUndo(s)!;
    expect(u.cmd).toEqual({ kind: "delete", detectionId: "b" });
    expect(u.state.undo).toHaveLength(1);
    expect(u.state.redo).toHaveLength(1);

    const r = popRedo(u.state)!;
    expect(r.cmd).toEqual({ kind: "delete", detectionId: "b" });
    expect(r.state.undo).toHaveLength(2);
    expect(r.state.redo).toHaveLength(0);
  });

  it("new push after undo clears redo branch", () => {
    let s = pushCommand(emptyStack(), { kind: "create", detectionId: "a" });
    s = popUndo(s)!.state;
    expect(s.redo).toHaveLength(1);
    s = pushCommand(s, { kind: "create", detectionId: "c" });
    expect(s.redo).toHaveLength(0);
    expect(s.undo).toHaveLength(1);
  });
});

describe("inversePatchFrom", () => {
  it("captures previous center and category", () => {
    const before = inversePatchFrom(
      {
        category: "switch" as const,
        subtype: "single_pole",
        center: { x: 10, y: 20 },
        bbox: { x0: 0, y0: 0, x1: 20, y1: 20 },
        confidence: 0.9,
        room_id: "r1",
        room_source: "manual",
      },
      {
        category: "light" as const,
        subtype: "recessed",
        center: { x: 30, y: 40 },
      },
    );
    expect(before).toMatchObject({
      category: "switch",
      subtype: "single_pole",
      center: { x: 10, y: 20 },
    });
  });
});
