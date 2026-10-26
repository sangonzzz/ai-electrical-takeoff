# From Agente 1 → Agente 5

## Done

`openpyxl` and `reportlab` added to `backend/pyproject.toml`.
`PIPELINE_VERSION` is now **0.5.0** (tagged).

```bash
uv sync --all-packages --group dev
uv run pytest backend/tests/test_exports.py -q
# Rebuild containers so image picks up deps:
docker compose up -d --build api worker
```
