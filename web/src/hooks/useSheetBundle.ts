import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDetection,
  createWireRun,
  deleteDetection,
  deleteWireRun,
  getSheet,
  getSheetBom,
  getSheetCorrections,
  isFixtureMode,
  patchDetection,
  patchWireRun,
  redoLastAction,
  restoreDetection,
  restoreWireRun,
  sheetImageUrl,
  undoLastAction,
} from "@/api/client";
import type {
  EntityMutationResponse,
  SheetBundle,
  WireRunCreateBody,
  WireRunPatchBody,
} from "@/api/types";
import type { Bom, Box, Detection, SheetResult, Takeoff, WireRun } from "@/types/contracts";
import {
  emptyStack,
  inversePatchFrom,
  inverseWirePatchFrom,
  popRedo,
  popUndo,
  pushCommand,
  type CommandStackState,
  type DetectionPatchBody,
  type HistoryCommand,
  type WirePatchBody,
} from "@/lib/commandStack";
import { wiresAfterDetectionMove } from "@/lib/wires";
import { useCanRedo, useCanUndo } from "./fixtureFlags";

export function sheetQueryKey(sheetId: string) {
  return ["sheet", sheetId] as const;
}

function ptPerFtOf(result: SheetResult): number {
  const s = result.sheet.scale_pt_per_ft;
  return typeof s === "number" && s > 0 ? s : 18;
}

export function useSheetBundle(sheetId: string) {
  const queryClient = useQueryClient();
  const fixtureCanUndo = useCanUndo();
  const fixtureCanRedo = useCanRedo();
  const fixture = isFixtureMode();

  const stackRef = useRef<CommandStackState>(emptyStack());
  const [stackEpoch, setStackEpoch] = useState(0);
  const applyingHistory = useRef(false);

  useEffect(() => {
    stackRef.current = emptyStack();
    setStackEpoch((n) => n + 1);
  }, [sheetId]);

  const bumpStack = useCallback((next: CommandStackState) => {
    stackRef.current = next;
    setStackEpoch((n) => n + 1);
  }, []);

  const sheetQuery = useQuery({
    queryKey: sheetQueryKey(sheetId),
    queryFn: () => getSheet(sheetId),
  });

  const bomQuery = useQuery({
    queryKey: ["bom", sheetId],
    queryFn: () => getSheetBom(sheetId),
    enabled: !!sheetQuery.data,
  });

  const correctionsQuery = useQuery({
    queryKey: ["corrections", sheetId],
    queryFn: () => getSheetCorrections(sheetId),
    enabled: !!sheetQuery.data,
  });

  function setResult(updater: (prev: SheetResult) => SheetResult) {
    queryClient.setQueryData(
      sheetQueryKey(sheetId),
      (old: Awaited<ReturnType<typeof getSheet>> | undefined) => {
        if (!old) return old;
        return { ...old, result: updater(old.result) };
      },
    );
  }

  function applyTakeoff(takeoff: Takeoff | undefined) {
    if (!takeoff) return;
    queryClient.setQueryData(
      sheetQueryKey(sheetId),
      (old: SheetBundle | undefined) => (old ? { ...old, takeoff } : old),
    );
  }

  function applyBom(bom: Bom | null | undefined) {
    if (bom === undefined) return;
    queryClient.setQueryData(["bom", sheetId], bom);
  }

  /** Merge optional derived fields from an entity mutation into the sheet cache. */
  function applyEntityMutation(data: EntityMutationResponse | DetectionMutationLike) {
    applyTakeoff(data.takeoff);
    if ("wire_runs" in data && data.wire_runs) {
      setResult((r) => ({ ...r, wire_runs: data.wire_runs as WireRun[] }));
    }
    if ("boxes" in data && data.boxes) {
      setResult((r) => ({ ...r, boxes: data.boxes as Box[] }));
    }
    if ("bom" in data && data.bom !== undefined) {
      applyBom(data.bom);
    }
  }

  async function refreshDerived() {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: sheetQueryKey(sheetId) }),
      queryClient.invalidateQueries({ queryKey: ["bom", sheetId] }),
      queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] }),
    ]);
  }

  function recordCommand(cmd: HistoryCommand) {
    if (fixture || applyingHistory.current) return;
    bumpStack(pushCommand(stackRef.current, cmd));
  }

  /** Apply inverse (undo) or forward (redo) through the API. */
  const playCommand = useCallback(
    async (cmd: HistoryCommand, direction: "undo" | "redo") => {
      applyingHistory.current = true;
      try {
        if (cmd.kind === "create") {
          if (direction === "undo") {
            await deleteDetection(cmd.detectionId);
          } else {
            await restoreDetection(cmd.detectionId, { history_action: "redo" });
          }
        } else if (cmd.kind === "delete") {
          if (direction === "undo") {
            await restoreDetection(cmd.detectionId, { history_action: "undo" });
          } else {
            await deleteDetection(cmd.detectionId);
          }
        } else if (cmd.kind === "wire_create") {
          if (direction === "undo") {
            await deleteWireRun(cmd.wireId);
          } else {
            await restoreWireRun(cmd.wireId, { history_action: "redo" });
          }
        } else if (cmd.kind === "wire_delete") {
          if (direction === "undo") {
            await restoreWireRun(cmd.wireId, { history_action: "undo" });
          } else {
            await deleteWireRun(cmd.wireId);
          }
        } else if (cmd.kind === "wire_update") {
          const body: WireRunPatchBody =
            direction === "undo"
              ? { ...cmd.before, history_action: "undo" }
              : { ...cmd.after, history_action: "redo" };
          await patchWireRun(cmd.wireId, body);
        } else {
          const body =
            direction === "undo"
              ? { ...cmd.before, history_action: "undo" as const }
              : { ...cmd.after, history_action: "redo" as const };
          await patchDetection(cmd.detectionId, body);
        }
        await refreshDerived();
      } finally {
        applyingHistory.current = false;
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sheetId, queryClient],
  );

  const createMut = useMutation({
    mutationFn: (
      body: Partial<Detection> & Pick<Detection, "category" | "subtype" | "center">,
    ) => createDetection(sheetId, body),
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId));
      const optimistic: Detection = {
        id: `optimistic-${crypto.randomUUID()}`,
        sheet_id: sheetId,
        category: body.category,
        subtype: body.subtype,
        codes: [],
        center: body.center,
        bbox: {
          x0: body.center.x - 8,
          y0: body.center.y - 8,
          x1: body.center.x + 8,
          y1: body.center.y + 8,
        },
        room_id: body.room_id ?? null,
        room_source: "manual",
        confidence: 1,
        source: "user",
        status: "active",
        needs_review: false,
        evidence: {},
      };
      setResult((r) => ({ ...r, detections: [...r.detections, optimistic] }));
      return { previous, optimisticId: optimistic.id };
    },
    onError: (_err, _body, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
    },
    onSuccess: (data, _body, ctx) => {
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) =>
          d.id === ctx?.optimisticId ? data.detection : d,
        ),
      }));
      applyTakeoff(data.takeoff);
      recordCommand({ kind: "create", detectionId: data.detection.id });
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
    },
  });

  const patchMut = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: DetectionPatchBody }) =>
      patchDetection(id, patch),
    onMutate: async ({ id, patch }) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId)) as
        | SheetBundle
        | undefined;
      const beforeDet = previous?.result.detections.find((d) => d.id === id);
      const beforePatch = beforeDet ? inversePatchFrom(beforeDet, patch) : {};
      const prevBom = queryClient.getQueryData(["bom", sheetId]) as Bom | null | undefined;
      setResult((r) => {
        const detections = r.detections.map((d) => {
          if (d.id !== id) return d;
          let next = { ...d, ...patch } as Detection;
          if (patch.center) {
            const dx = patch.center.x - d.center.x;
            const dy = patch.center.y - d.center.y;
            next = {
              ...next,
              center: patch.center,
              bbox: {
                x0: d.bbox.x0 + dx,
                y0: d.bbox.y0 + dy,
                x1: d.bbox.x1 + dx,
                y1: d.bbox.y1 + dy,
              },
            };
          }
          return next;
        });
        let wire_runs = r.wire_runs ?? [];
        if (patch.center) {
          wire_runs = wiresAfterDetectionMove(wire_runs, id, patch.center, ptPerFtOf(r));
        }
        return { ...r, detections, wire_runs };
      });
      return { previous, beforePatch, afterPatch: patch, prevBom };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
      if (ctx?.prevBom !== undefined) {
        queryClient.setQueryData(["bom", sheetId], ctx.prevBom);
      }
    },
    onSuccess: (data, { id }, ctx) => {
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) => (d.id === id ? data.detection : d)),
        ...(data.wire_runs ? { wire_runs: data.wire_runs } : {}),
        ...(data.boxes ? { boxes: data.boxes } : {}),
      }));
      applyTakeoff(data.takeoff);
      if (data.bom !== undefined) applyBom(data.bom);
      if (ctx?.beforePatch && ctx.afterPatch) {
        recordCommand({
          kind: "update",
          detectionId: id,
          before: ctx.beforePatch,
          after: ctx.afterPatch,
        });
      }
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      if (data.bom === undefined) {
        void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
      }
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteDetection(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId)) as
        | SheetBundle
        | undefined;
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) =>
          d.id === id ? { ...d, status: "deleted" as const } : d,
        ),
      }));
      return { previous };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
    },
    onSuccess: (data, id) => {
      applyTakeoff(data.takeoff);
      recordCommand({ kind: "delete", detectionId: id });
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
    },
  });

  const createWireMut = useMutation({
    mutationFn: (body: WireRunCreateBody) => createWireRun(sheetId, body),
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId)) as
        | SheetBundle
        | undefined;
      const prevBom = queryClient.getQueryData(["bom", sheetId]) as Bom | null | undefined;
      const optimisticId = `optimistic-wire-${crypto.randomUUID()}`;
      const vertical = body.vertical_allowance_ft ?? 0;
      const optimistic: WireRun = {
        id: optimisticId,
        sheet_id: sheetId,
        points: body.points,
        from_detection_id: body.from_detection_id ?? null,
        to_detection_id: body.to_detection_id ?? null,
        cable_type: body.cable_type,
        plan_length_ft: body.plan_length_ft,
        vertical_allowance_ft: vertical,
        total_length_ft: body.total_length_ft ?? body.plan_length_ft + vertical,
        confidence: body.confidence ?? 1,
        source: "user",
      };
      setResult((r) => ({
        ...r,
        wire_runs: [...(r.wire_runs ?? []), optimistic],
      }));
      return { previous, prevBom, optimisticId };
    },
    onError: (_err, _body, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
      if (ctx?.prevBom !== undefined) {
        queryClient.setQueryData(["bom", sheetId], ctx.prevBom);
      }
    },
    onSuccess: (data, _body, ctx) => {
      if (data.wire_run && ctx?.optimisticId) {
        setResult((r) => ({
          ...r,
          wire_runs: (r.wire_runs ?? []).map((w) =>
            w.id === ctx.optimisticId ? (data.wire_run as WireRun) : w,
          ),
        }));
        recordCommand({ kind: "wire_create", wireId: data.wire_run.id });
      }
      applyEntityMutation(data);
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      if (data.bom === undefined) {
        void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
      }
    },
  });

  const patchWireMut = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: WireRunPatchBody }) =>
      patchWireRun(id, patch),
    onMutate: async ({ id, patch }) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId)) as
        | SheetBundle
        | undefined;
      const prevBom = queryClient.getQueryData(["bom", sheetId]) as Bom | null | undefined;
      const beforeWire = previous?.result.wire_runs?.find((w) => w.id === id);
      const beforePatch = beforeWire
        ? inverseWirePatchFrom(beforeWire, patch as WirePatchBody)
        : {};
      setResult((r) => ({
        ...r,
        wire_runs: (r.wire_runs ?? []).map((w) =>
          w.id === id ? ({ ...w, ...patch } as WireRun) : w,
        ),
      }));
      return { previous, prevBom, beforePatch, afterPatch: patch as WirePatchBody };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
      if (ctx?.prevBom !== undefined) {
        queryClient.setQueryData(["bom", sheetId], ctx.prevBom);
      }
    },
    onSuccess: (data, { id }, ctx) => {
      if (data.wire_run) {
        setResult((r) => ({
          ...r,
          wire_runs: (r.wire_runs ?? []).map((w) => (w.id === id ? data.wire_run! : w)),
        }));
      }
      applyEntityMutation(data);
      if (ctx?.beforePatch && ctx.afterPatch) {
        recordCommand({
          kind: "wire_update",
          wireId: id,
          before: ctx.beforePatch,
          after: ctx.afterPatch,
        });
      }
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      if (data.bom === undefined) {
        void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
      }
    },
  });

  const deleteWireMut = useMutation({
    mutationFn: (id: string) => deleteWireRun(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId)) as
        | SheetBundle
        | undefined;
      const prevBom = queryClient.getQueryData(["bom", sheetId]) as Bom | null | undefined;
      setResult((r) => ({
        ...r,
        wire_runs: (r.wire_runs ?? []).filter((w) => w.id !== id),
      }));
      return { previous, prevBom };
    },
    onError: (_err, _id, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
      if (ctx?.prevBom !== undefined) {
        queryClient.setQueryData(["bom", sheetId], ctx.prevBom);
      }
    },
    onSuccess: (data, id) => {
      applyEntityMutation(data);
      recordCommand({ kind: "wire_delete", wireId: id });
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      if (data.bom === undefined) {
        void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
      }
    },
  });

  function applyHistoryBundle(bundle: SheetBundle | null) {
    if (!bundle) return;
    queryClient.setQueryData(sheetQueryKey(sheetId), bundle);
    void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
    void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
  }

  const undoMut = useMutation({
    mutationFn: () => undoLastAction(sheetId),
    onSuccess: applyHistoryBundle,
  });

  const redoMut = useMutation({
    mutationFn: () => redoLastAction(sheetId),
    onSuccess: applyHistoryBundle,
  });

  const [historyBusy, setHistoryBusy] = useState(false);

  const undo = useCallback(() => {
    if (fixture) {
      undoMut.mutate();
      return;
    }
    const popped = popUndo(stackRef.current);
    if (!popped || historyBusy) return;
    bumpStack(popped.state);
    setHistoryBusy(true);
    void playCommand(popped.cmd, "undo").finally(() => setHistoryBusy(false));
  }, [fixture, historyBusy, bumpStack, undoMut, playCommand]);

  const redo = useCallback(() => {
    if (fixture) {
      redoMut.mutate();
      return;
    }
    const popped = popRedo(stackRef.current);
    if (!popped || historyBusy) return;
    bumpStack(popped.state);
    setHistoryBusy(true);
    void playCommand(popped.cmd, "redo").finally(() => setHistoryBusy(false));
  }, [fixture, historyBusy, bumpStack, redoMut, playCommand]);

  void stackEpoch;
  const canUndo = fixture ? fixtureCanUndo : stackRef.current.undo.length > 0 && !historyBusy;
  const canRedo = fixture ? fixtureCanRedo : stackRef.current.redo.length > 0 && !historyBusy;

  return {
    sheetQuery,
    bomQuery,
    correctionsQuery,
    imageUrl: sheetImageUrl(sheetId),
    createDetection: createMut.mutate,
    patchDetection: (id: string, patch: DetectionPatchBody) =>
      patchMut.mutate({ id, patch }),
    deleteDetection: deleteMut.mutate,
    createWireRun: createWireMut.mutate,
    patchWireRun: (id: string, patch: WireRunPatchBody) =>
      patchWireMut.mutate({ id, patch }),
    deleteWireRun: deleteWireMut.mutate,
    undo,
    redo,
    canUndo,
    canRedo,
    /** Local-only move for drag frames (no network); snaps attached wire tips. */
    applyLocalMove: (id: string, x: number, y: number) => {
      setResult((r) => {
        const detections = r.detections.map((d) => {
          if (d.id !== id) return d;
          const dx = x - d.center.x;
          const dy = y - d.center.y;
          return {
            ...d,
            center: { x, y },
            bbox: {
              x0: d.bbox.x0 + dx,
              y0: d.bbox.y0 + dy,
              x1: d.bbox.x1 + dx,
              y1: d.bbox.y1 + dy,
            },
          };
        });
        const wire_runs = wiresAfterDetectionMove(
          r.wire_runs ?? [],
          id,
          { x, y },
          ptPerFtOf(r),
        );
        return { ...r, detections, wire_runs };
      });
    },
  };
}

/** Shape shared by detection PATCH and entity mutation responses. */
type DetectionMutationLike = {
  takeoff: Takeoff;
  wire_runs?: WireRun[];
  boxes?: Box[];
  bom?: Bom | null;
};
