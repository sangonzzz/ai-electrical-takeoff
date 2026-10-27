# Please bump PIPELINE_VERSION (R7)

Agente 2 finished the last engine round. Behavior changed in:

- `viewport.py` — soft ELECTRICAL/POWER/LIGHTING PLAN titles; largest-drawing fallback + warning
- `legend.py` — builtin catalog when LEGEND missing + warning
- `classify.py` / symbols (already in `273d3e7`) — attic light + sink half-hot
- `pipeline.py` — wires warnings into viewport/legend/scale fallbacks

Escondido path unchanged (tests green). Generalization probe no longer raises.

Please bump at least the **patch** on `PIPELINE_VERSION` in `engine/takeoff_engine/__init__.py` and push when ready.

Cómo verificar:

```bash
uv run pytest engine/tests/symbols/ -q
uv run python eval/scripts/generalization_probe.py
```
