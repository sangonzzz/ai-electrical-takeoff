# Agente 2 — Symbol engine (viewport, legend, symbols, classify, pipeline)

## Estado

Round 2 fixes 1–8 **committed locally** (ahead of `origin/main`). `needs_review` tightened to ~5%. **Needs Agente 1 to push.**

## Hecho

### Round 2 (local SHAs, not yet on GitHub as of this status)

| # | Commit | Fix |
|---|--------|-----|
| 1 | `420b5cd` | junction_box = small J-circle only |
| 2 | `eee3918` | SD/SD/MA text → center-dot |
| 3 | `7ed0d8d` | EXT → exterior_wall (**last on origin**) |
| 4 | `37d9285` | half-fill exhaust (not duplex); IAQ |
| 5 | `72df08b` | AFCI half-hot from duplex half-fill |
| 6 | `70606cf` | cross-category NMS (detector > light) |
| 7 | `8d44973` | wall light = circle+cross+tick |
| 8 | `f985438` | IN ATTIC light+switch |
| — | `f2f4fc3` | docs + msg A7 |
| — | *(new)* | `needs_review` only cross-cat / weak uncoded (~5%) |

### needs_review

Was ~75–90% (same-glyph receptacle rows within 0.01). Now only when top-two are **different categories** and close, or weak score with no codes. Plan 1–4: **4–6%**.

## Cómo probarlo

```bash
uv run pytest engine/tests/symbols/ -q
uv run takeoff analyze data/plans/escondido_plans.pdf --page 1 --out out/plan1.json --debug --no-llm --no-bom
# pages 1..4
```

## Siguiente

- Agente 1: push `origin/main` through latest A2 commits
- Agente 7: re-run eval after push

## Bloqueos

- **Push:** only Agente 1 pushes; local is 6+ commits ahead of origin (items 4–8 + docs + needs_review).

## Decisions

- `needs_review`: ignore same-category legend ties; codes own subtype.
- Half-disc: 2 duplex slots → half-hot; 4 circle chords → exhaust.

## Needs from Santiago

- Ask Agente 1 to push, or confirm push so GitHub matches local round 2.

## Explicación para Santiago

Los fixes 4–8 de la ronda 2 ya están hechos y commiteados en tu máquina (exhaust, half-hot, NMS, wall light, ático), pero GitHub se quedó en el fix 3 (EXT) porque solo Agente 1 hace push. Además bajé `needs_review` de ~80% a ~5%: antes casi todos los tomacorrientes salían “a revisar” porque GFCI/AFCI/duplex se parecen en el dibujo; ahora solo se marca si compiten **categorías distintas** o el match es flojo y sin código. Pedí a Agente 1 que suba esos commits.
