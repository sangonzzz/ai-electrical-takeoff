import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createDetection,
  deleteDetection,
  getSheet,
  getSheetBom,
  getSheetCorrections,
  patchDetection,
  sheetImageUrl,
  undoLastAction,
} from "@/api/client";
import type { Detection, SheetResult } from "@/types/contracts";
import { useCanUndo } from "./fixtureFlags";

export function sheetQueryKey(sheetId: string) {
  return ["sheet", sheetId] as const;
}

export function useSheetBundle(sheetId: string) {
  const queryClient = useQueryClient();
  const canUndo = useCanUndo();

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
    queryClient.setQueryData(sheetQueryKey(sheetId), (old: Awaited<ReturnType<typeof getSheet>> | undefined) => {
      if (!old) return old;
      return { ...old, result: updater(old.result) };
    });
  }

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
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
    },
  });

  const patchMut = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<Detection> }) =>
      patchDetection(id, patch),
    onMutate: async ({ id, patch }) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId));
      setResult((r) => ({
        ...r,
        detections: r.detections.map((d) => {
          if (d.id !== id) return d;
          let next = { ...d, ...patch };
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
      return { previous };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(sheetQueryKey(sheetId), ctx.previous);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteDetection(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: sheetQueryKey(sheetId) });
      const previous = queryClient.getQueryData(sheetQueryKey(sheetId));
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
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
      void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
    },
  });

  const undoMut = useMutation({
    mutationFn: () => undoLastAction(sheetId),
    onSuccess: (bundle) => {
      if (bundle) {
        queryClient.setQueryData(sheetQueryKey(sheetId), bundle);
        void queryClient.invalidateQueries({ queryKey: ["corrections", sheetId] });
        void queryClient.invalidateQueries({ queryKey: ["bom", sheetId] });
      }
    },
  });

  return {
    sheetQuery,
    bomQuery,
    correctionsQuery,
    imageUrl: sheetImageUrl(sheetId),
    createDetection: createMut.mutate,
    patchDetection: (id: string, patch: Partial<Detection>) =>
      patchMut.mutate({ id, patch }),
    deleteDetection: deleteMut.mutate,
    undo: () => undoMut.mutate(),
    canUndo,
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
