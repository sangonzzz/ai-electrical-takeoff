# From Agente 5 → Agente 6

## Excel + PDF quote exports ready

Wire download buttons (sheet panel + document/home):

| Method | Path | File |
|--------|------|------|
| GET | `/api/sheets/{sheet_id}/export.xlsx` | takeoff workbook |
| GET | `/api/sheets/{sheet_id}/quote.pdf` | client quote |
| GET | `/api/documents/{document_id}/export.xlsx` | all 4 plans in one workbook |
| GET | `/api/documents/{document_id}/quote.pdf` | all 4 plans in one PDF |

Existing: `/api/sheets/{id}/export.csv` still works.

Suggested UI labels: **Export Excel**, **Download quote (PDF)** on the sheet view;
on the home/document list after jobs succeed: **Export all (Excel)** / **Quote all (PDF)**.

Response is a file download (`Content-Disposition: attachment`). Use `window.open` or
`fetch` + blob download with auth-free same-origin `/api` proxy.
