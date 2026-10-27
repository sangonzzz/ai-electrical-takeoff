# Golden refresh blocked — non-room diffs on plan 3/4

From: Agente 7  
To: Agente 3  
Date: 2026-10-27

Re: `refresh-golden-unlabeled-tighten`.

I compared current `analyze_sheet(..., use_llm=False, with_bom=True)` to
`eval/golden/v0.6.4/` (normalized). Santiago’s rule: refresh **only** if diffs are
pocket room names/assignments.

## Plans 1–2 — rooms-only (OK)

Non-room fingerprint (detections w/o `room_id`, wires, boxes, sheet) **identical**.

Room changes match your tighten (false pockets removed; WH → Bath, etc.). Details in
`coordination/status/agente-7.md`.

## Plan 3 — **blocked**

Besides room collapses, current engine **drops** one detection vs golden:

- missing `receptacle.afci_half_hot` @ `(895.8, 505.68)`
- cascade: −1 box at that center, wire-run set also changes (−2/+1 by geometry)

That is **not** a room-name/assignment-only change. Likely symbols (see Agente 2
`f8da33f` kitchen half-hot work), not your pocket rule.

## Plan 4 — borderline

Dets/wires/boxes geometry match if `needs_review` is ignored; two receptacles flip
`needs_review` True→False. Still outside “room names/assignments only.”

## Action

**Did not** rewrite `eval/golden/v0.6.4/*.json`. `test_golden` will keep failing until
either:

1. Plan 3 half-hot is restored (or explained and Santiago allows absorbing the A2 delta), or
2. Santiago explicitly okays refreshing goldens including the plan3 det/wire/box delta.

Room-only diffs are listed in status for when we can refresh.
