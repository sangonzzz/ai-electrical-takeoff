"""Compare current analyze_sheet fingerprints to eval/golden/v0.6.4.

Reports whether non-room fields (detections sans room_id, wires, boxes, sheet)
are unchanged — required before refreshing goldens after intentional room edits.
"""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from eval.golden_normalize import (  # noqa: E402
    DEFAULT_PDF,
    GOLDEN_DIR,
    load_golden,
    normalize_sheet_result,
)
from takeoff_engine.pipeline import analyze_sheet  # noqa: E402


def strip_room_fields(fp: dict[str, Any]) -> dict[str, Any]:
    """Fingerprint with rooms removed and detection.room_id cleared."""
    out = deepcopy(fp)
    out.pop("rooms", None)
    for det in out.get("detections") or []:
        det["room_id"] = None
    return out


def summarize_room_diff(old: dict[str, Any], new: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    old_rooms = {r["id"]: r for r in old.get("rooms") or []}
    new_rooms = {r["id"]: r for r in new.get("rooms") or []}
    # Compare by display_name / centroid since ids are order-stable keys
    old_by_name = sorted(
        (r.get("display_name"), r.get("centroid"), r.get("kind")) for r in old_rooms.values()
    )
    new_by_name = sorted(
        (r.get("display_name"), r.get("centroid"), r.get("kind")) for r in new_rooms.values()
    )
    if old_by_name != new_by_name:
        lines.append(f"  room count: {len(old_rooms)} → {len(new_rooms)}")
        old_names = [r.get("display_name") for r in old.get("rooms") or []]
        new_names = [r.get("display_name") for r in new.get("rooms") or []]
        removed = [n for n in old_names if n not in new_names]
        added = [n for n in new_names if n not in old_names]
        if removed:
            lines.append(f"  rooms removed: {removed}")
        if added:
            lines.append(f"  rooms added: {added}")
        # renamed / same count but different set
        both = set(old_names) & set(new_names)
        if len(both) < min(len(old_names), len(new_names)):
            lines.append(f"  rooms unchanged names: {sorted(both)}")

    # Detection room assignment shifts (by stable det key after normalize)
    # Keys may reshuffle if room sort order changes — compare by det geometry key
    def det_key(d: dict[str, Any]) -> tuple:
        c = d.get("center") or {}
        return (d.get("category"), d.get("subtype"), c.get("x"), c.get("y"))

    old_dets = {det_key(d): d for d in old.get("detections") or []}
    new_dets = {det_key(d): d for d in new.get("detections") or []}
    assign_changes = 0
    samples: list[str] = []
    for k, od in old_dets.items():
        nd = new_dets.get(k)
        if not nd:
            continue
        # Map room keys to display names
        old_rid = od.get("room_id")
        new_rid = nd.get("room_id")
        old_name = next(
            (r["display_name"] for r in (old.get("rooms") or []) if r["id"] == old_rid),
            old_rid,
        )
        new_name = next(
            (r["display_name"] for r in (new.get("rooms") or []) if r["id"] == new_rid),
            new_rid,
        )
        if old_name != new_name:
            assign_changes += 1
            if len(samples) < 12:
                samples.append(
                    f"    {od.get('category')}.{od.get('subtype')} @ {k[2]},{k[3]}: "
                    f"{old_name!r} → {new_name!r}"
                )
    if assign_changes:
        lines.append(f"  detection room_id reassignments: {assign_changes}")
        lines.extend(samples)
    return lines


def main() -> int:
    ok_non_room = True
    report: list[str] = []
    for plan in range(1, 5):
        golden_path = GOLDEN_DIR / f"plan{plan}.json"
        old = load_golden(golden_path)
        print(f"analyze plan{plan} …", flush=True)
        result = analyze_sheet(DEFAULT_PDF, plan - 1, use_llm=False, with_bom=True)
        new = normalize_sheet_result(result)

        non_old = strip_room_fields(old)
        non_new = strip_room_fields(new)
        non_room_equal = non_old == non_new
        if not non_room_equal:
            ok_non_room = False
            # Find rough path of first difference
            report.append(f"plan{plan}: NON-ROOM DIFF (refuse refresh)")
            dump = REPO / "out" / "debug" / f"golden_nonroom_diff_plan{plan}.json"
            dump.parent.mkdir(parents=True, exist_ok=True)
            dump.write_text(
                json.dumps({"old": non_old, "new": non_new}, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            report.append(f"  wrote {dump}")
        else:
            report.append(f"plan{plan}: non-room fingerprint IDENTICAL")

        room_lines = summarize_room_diff(old, new)
        if room_lines:
            report.append(f"plan{plan}: room-related changes:")
            report.extend(room_lines)
        else:
            report.append(f"plan{plan}: rooms also identical")

    print("\n".join(report))
    out = REPO / "out" / "debug" / "golden_room_diff_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Golden vs current\n\n" + "\n".join(report) + "\n", encoding="utf-8")
    print(f"\nwrote {out}")
    return 0 if ok_non_room else 1


if __name__ == "__main__":
    raise SystemExit(main())
