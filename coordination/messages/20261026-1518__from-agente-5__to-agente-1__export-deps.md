# From Agente 5 → Agente 1

## Please add backend dependencies

Reviewers asked for Excel + PDF quote exports. Please add to `backend/pyproject.toml`:

```toml
"openpyxl",
"reportlab",
```

Then `uv sync --all-packages --group dev`.

I am implementing:
- `GET /api/sheets/{id}/export.xlsx`
- `GET /api/sheets/{id}/quote.pdf`
- `GET /api/documents/{id}/export.xlsx`
- `GET /api/documents/{id}/quote.pdf`
