"""Run analyze_sheet on non-Escondido public plans; write overlays + summary JSON.

Owned by Agente 7. Does not tune the engine — observation only.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from takeoff_engine.overlay import render_overlay
from takeoff_engine.pipeline import analyze_sheet

REPO = Path(__file__).resolve().parents[2]
OUT_JSON = REPO / "out" / "generalization"
OUT_PNG = REPO / "out" / "debug" / "generalization"
REPORT = REPO / "eval" / "reports" / "generalization"

CASES = [
    # Longview TX residential template — page 4 looks like the electrical example.
    ("longview", REPO / "data/plans/generalization/longview_residential_template.pdf", [4]),
    # Palm Beach Gardens FL — electrical legend + floor power plans (commercial-ish).
    ("pbg", REPO / "data/plans/generalization/pbg_electrical.pdf", [0, 1]),
]


def main() -> None:
    OUT_JSON.mkdir(parents=True, exist_ok=True)
    OUT_PNG.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    for name, pdf, pages in CASES:
        if not pdf.is_file():
            rows.append({"plan": name, "ok": False, "error": f"missing {pdf}"})
            continue
        for page in pages:
            entry: dict = {"plan": name, "pdf": str(pdf.relative_to(REPO)), "page": page}
            try:
                print(f"ANALYZE {name} page {page}...", flush=True)
                result = analyze_sheet(pdf, page, use_llm=False, with_bom=False)
                jpath = OUT_JSON / f"{name}_p{page}.json"
                ppath = OUT_PNG / f"{name}_p{page}_overlay.png"
                jpath.write_text(result.model_dump_json(indent=2), encoding="utf-8")
                try:
                    render_overlay(pdf, result, ppath)
                    entry["overlay"] = str(ppath.relative_to(REPO)).replace("\\", "/")
                except Exception as oe:  # noqa: BLE001
                    entry["overlay_error"] = str(oe)
                active = [d for d in result.detections if d.status != "deleted"]
                cats: dict[str, int] = {}
                for d in active:
                    cats[d.category.value] = cats.get(d.category.value, 0) + 1
                entry.update(
                    {
                        "ok": True,
                        "detections": len(active),
                        "rooms": len(result.rooms),
                        "legend": len(result.legend),
                        "title": result.sheet.title,
                        "sheet_number": result.sheet.sheet_number,
                        "viewport": result.sheet.viewport.model_dump(),
                        "warnings": list(result.warnings[:15]),
                        "by_category": cats,
                        "result_json": str(jpath.relative_to(REPO)).replace("\\", "/"),
                    }
                )
                print(
                    f"  dets={entry['detections']} rooms={entry['rooms']} "
                    f"legend={entry['legend']} title={entry['title']}",
                    flush=True,
                )
            except Exception as e:  # noqa: BLE001
                entry["ok"] = False
                entry["error"] = f"{type(e).__name__}: {e}"
                entry["traceback"] = traceback.format_exc()[-2000:]
                print(f"  FAIL {entry['error']}", flush=True)
            rows.append(entry)

    (REPORT / "summary.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    md = ["# Generalization probe", ""]
    for r in rows:
        md.append(f"## {r.get('plan')} page {r.get('page')}")
        md.append("")
        if not r.get("ok"):
            md.append(f"- **FAIL:** `{r.get('error')}`")
        else:
            md.append(f"- title: `{r.get('title')}`")
            md.append(f"- detections: **{r.get('detections')}** `{r.get('by_category')}`")
            md.append(f"- rooms: {r.get('rooms')} · legend entries: {r.get('legend')}")
            md.append(f"- viewport: `{r.get('viewport')}`")
            md.append(f"- overlay: `{r.get('overlay')}`")
            if r.get("warnings"):
                md.append("- warnings:")
                for w in r["warnings"]:
                    md.append(f"  - {w}")
        md.append("")
    (REPORT / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"WROTE {REPORT / 'summary.md'}")


if __name__ == "__main__":
    main()
