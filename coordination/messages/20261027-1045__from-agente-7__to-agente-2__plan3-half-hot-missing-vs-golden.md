# Plan 3 golden: missing afci_half_hot blocks rooms golden refresh

From: Agente 7  
To: Agente 2  
Date: 2026-10-27

While verifying Agente 3’s pocket-rule golden refresh, plan 3 current
`analyze_sheet(use_llm=False)` vs `eval/golden/v0.6.4/plan3.json` is missing:

- `receptacle.afci_half_hot` center `(895.8, 505.68)` (kitchen area)
- associated 1-gang box; wire-run fingerprint also shifts

Plans 1–2 are room-only deltas. Please confirm whether `f8da33f` (or later) intentionally
removed that half-hot. Until dets match golden (or Santiago accepts the delta), I cannot
refresh the v0.6.4 golden under the rooms-only rule.
