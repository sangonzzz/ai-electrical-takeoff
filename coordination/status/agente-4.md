# Agente 4 — AI with Claude (llm/)

## Estado

Adjudication safety: **flag_only** (legend + flagging). Never delete strong evidence; never create detections. Diff vs no-LLM is count-neutral on all 4 plans.

## Hecho

### Diff: ENABLE_LLM on vs off (local Escondido, match by center ±0.1 pt)

#### Before fix (delete/`not_a_component` allowed)

| Plan | page | n no-LLM | n LLM | added | removed | relabeled |
|------|------|----------|-------|-------|---------|-----------|
| 1 | 0 | 53 | 53 | 0 | 0 | 0 |
| 2 | 1 | 64 | 64 | 0 | 0 | 0 |
| 3 | 2 | 68 | **67** | 0 | **1** | 0 |
| 4 | 3 | 82 | 82 | 0 | 0 | 0 |

Removed (Plan 3): `receptacle.gfci_weatherproof` @ (926.3, 375.8), match≈0.39, no codes — dropped as `not_a_component`.

Local Plan 1 was already count-identical; Docker Plan 1 loss (240V GFI) / false exterior exhaust matches the old pipeline path that **deleted** on `not_a_component` and **relabeled** freely (and exterior exhaust should then hit `drop_outside_footprint` unless EXT/WP — false exhaust implies a bad relabel that survived or ran before footprint drop).

**Verdict: net negative** → keep LLM for **legend interpretation + flagging only**.

#### After fix (`apply_adjudications(..., mode="flag_only")`)

| Plan | page | n no-LLM | n LLM | added | removed | relabeled | flagged only |
|------|------|----------|-------|-------|---------|-----------|--------------|
| 1 | 0 | 53 | 53 | 0 | 0 | 0 | 0 |
| 2 | 1 | 64 | 64 | 0 | 0 | 0 | 0 |
| 3 | 2 | 68 | 68 | 0 | 0 | 0 | 2 |
| 4 | 3 | 82 | 82 | 0 | 0 | 0 | 0 |

Plan 3 flags: (926.3, 375.8) `llm=not_a_component` kept as WP receptacle + `needs_review`; (1163.3, 675.2) exterior light opinion recorded, geometry label unchanged.

### Code

- `llm/apply.py`: `apply_adjudications` + `has_strong_evidence` (match≥0.8 or codes/tokens).
- Default mode **`flag_only`**: attach `llm_label`/`llm_reason`, set `needs_review`; no delete; no category/subtype change; no creates.
- `safe_relabel` mode available (subtype-only on strong; weak may drop on `not_a_component`) — not used in pipeline.
- `pipeline.py` LLM block wired to `apply_adjudications` (messaged Agente 2).
- Prompt `adjudicate_v1.md` updated.

## Cómo probarlo

```bash
uv run pytest engine/tests/llm -q
# with vs without LLM counts should match:
uv run python -c "from pathlib import Path; from takeoff_engine.pipeline import analyze_sheet as a; p=Path('data/plans/escondido_plans.pdf');
print([(i,len(a(p,i,use_llm=False).detections),len(a(p,i,use_llm=True).detections)) for i in range(4)])"
```

## Siguiente

- Agente 1: bump `PIPELINE_VERSION` (freeze) after this safety fix.
- Optional later: re-enable `safe_relabel` only if eval shows net positive.

## Bloqueos

- Version bump needs Agente 1.

## Decisions

- LLM adjudication default = **flag_only** after net-negative delete behavior.
- Strong evidence = `match_score >= 0.8` OR any `codes` / `text_tokens`.
- Exterior EXT/WP still enforced by Agente 2 `drop_outside_footprint` (unchanged).

## Needs from Santiago

- (none for keys). Please have Agente 1 bump pipeline version.

## Explicación para Santiago

El LLM no debe borrar ni inventar símbolos: solo puede opinar. Antes, si decía `not_a_component`, el pipeline borraba la detección — por eso en Docker se podía perder el GFI 240V y aparecer basura. Medí las 4 plantas: con el modo viejo Plan 3 perdía 1 receptáculo; con el arreglo **ninguna planta cambia el conteo**, solo se marcan 2 cosas en Plan 3 para revisión. La leyenda con Haiku se mantiene; la adjudicación solo pone bandera `needs_review`.
