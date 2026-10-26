# From Agente 5 → Agente 6

## Show the PDF content hash in the sheet header

The original upload is stored byte-for-byte; analysis and the plan PNG both use that file.
Please show a short form of `file_hash` in the sheet header (e.g. first 8 hex chars) so Santiago
can verify which PDF is on screen.

## Where to read it

| Endpoint | Field |
|----------|--------|
| `POST /api/documents` / `/demo` | `file_hash` (top-level) and `sheets[].file_hash` |
| `GET /api/documents/{id}` | `file_hash` + `sheets[].file_hash` |
| `GET /api/sheets/{id}` | `file_hash` (sibling of `sheet`) |

Example: `file_hash: "a1b2c3d4e5f6..."` → display `a1b2c3d4` (or `a1b2c3d4…`).

Tooltip can say “SHA-256 of original PDF (unchanged)”.
