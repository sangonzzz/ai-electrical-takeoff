# From Agente 1 → Agente 2

## PIPELINE_VERSION (single source)

- Defined only in `engine/takeoff_engine/__init__.py` as `PIPELINE_VERSION = __version__ = "0.3.0"`.
- I updated `pipeline.py` to `from takeoff_engine import PIPELINE_VERSION` and removed the local `0.2.0-a2` constant (integration fix).
- **Rule (AGENTS.md §13):** any behavior change in viewport/legend/symbols/classify/pipeline → ask Agente 1 to bump at least the **patch**, so idempotency does not reuse stale runs.

```bash
uv run takeoff --version   # 0.3.0
```
