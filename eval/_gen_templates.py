"""One-shot helper to regenerate ground-truth count templates. Not part of runtime."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.models import SUBTYPES

KEYS = [f"{cat}.{s}" for cat, subs in SUBTYPES.items() for s in subs]

PLANS: dict[int, dict[str, object]] = {
    1: {
        "title": "Plan 1 — studio (sheet A1-111)",
        "rooms": [
            "Bath",
            "Bedroom / Studio",
            "CL 1",
            "CL 2",
            "Kitchen / Dining",
            "Living",
            "Laundry",
            "Attic",
            "Exterior",
        ],
    },
    2: {
        "title": "Plan 2 — 2 bedrooms (sheet A2-111)",
        "rooms": [
            "Bath",
            "Bed 1",
            "Bed 2",
            "CL 1",
            "CL 2",
            "Dining",
            "Hallway",
            "Kitchen",
            "Living",
            "Laundry",
            "Attic",
            "Exterior",
        ],
    },
    3: {
        "title": "Plan 3 — 2 bedrooms (sheet A3-111)",
        # display_name list from Agente 3 detect_rooms (four closet labels).
        "rooms": [
            "Bath 1",
            "Bath 2",
            "Bed 1",
            "Bed 2",
            "CL 1",
            "CL 2",
            "CL 3",
            "CL 4",
            "Hall",
            "Kitchen / Dining",
            "Living",
            "Laundry",
            "Attic",
            "Exterior",
        ],
    },
    4: {
        "title": "Plan 4 — 3 bedrooms (sheet A4-111)",
        # display_name list from Agente 3 detect_rooms (two closet labels).
        "rooms": [
            "Bath 1",
            "Bath 2",
            "Bed 1",
            "Bed 2",
            "CL 1",
            "CL 2",
            "Hallway",
            "Kitchen",
            "Living",
            "Laundry",
            "Optional Bed 3",
            "Walk-In Closet",
            "Attic",
            "Exterior",
        ],
    },
}


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "ground_truth"
    out_dir.mkdir(parents=True, exist_ok=True)
    for n, meta in PLANS.items():
        title = meta["title"]
        rooms = meta["rooms"]
        assert isinstance(title, str) and isinstance(rooms, list)
        lines = [
            f"# {title}",
            "# Template for hand counts. Every category.subtype starts at 0.",
            "# Instructions: eval/COMO_CONTAR.md — do NOT look at system output while counting.",
            "# Room names from SPEC section 1 (+ Attic / Exterior per DECISIONS).",
            "",
        ]
        for room in rooms:
            lines.append(f"{room}:")
            for k in KEYS:
                lines.append(f"  {k}: 0")
            lines.append("")
        path = out_dir / f"plan{n}.counts.yaml"
        path.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {path} ({len(rooms)} rooms, {len(KEYS)} keys each)")


if __name__ == "__main__":
    main()
