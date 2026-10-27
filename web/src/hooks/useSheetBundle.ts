import { useCallback, useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDetection,
  deleteDetection,
  getSheet,
  getSheetBom,
  getSheetCorrections,
  isFixtureMode,
  patchDetection,
  redoLastAction,
  restoreDetection,
  sheetImageUrl,
  undoLastAction,
} from "@/api/client";
import type { SheetBundle } from "@/api/types";
import type { Detection, SheetResult, Takeoff } from "@/types/contracts";
import {
  emptyStack,
  inversePatchFrom,
  popRedo,
  popUndo,
  pushCommand,
  type CommandStackState,
  type DetectionPatchBody,
  type HistoryCommand,
} from "@/lib/commandStack";
import { useCanRedo, useCanUndo } from "./fixtureFlags";

export function sheetQueryKey(sheetId: string) {
  return ["sheet", sheetId] as const;
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
    // refreshDerived closes over sheetId/queryClient — recreate when sheet changes
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
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) => {
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
        }),
      }));
      return { previous, beforePatch, afterPatch: patch };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
    },
    onSuccess: (data, { id }, ctx) => {
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) => (d.id === id ? data.detection : d)),
      }));
      applyTakeoff(data.takeoff);
      if (ctx?.beforePatch && ctx.afterPatch) {
        recordCommand({
          kind: "update",
          detectionId: id,
          before: ctx.beforePatch,
          after: ctx.afterPatch,
        });
      }
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
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
    undo,
    redo,
    canUndo,
    canRedo,
    /** Local-only move for drag frames (no network). */
    applyLocalMove: (id: string, x: number, y: number) => {
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) => {
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
        }),
      }));
    },
  };
}
