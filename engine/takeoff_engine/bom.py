"""Bill of materials aggregation (owned by Agente 8).

``compute_bom`` is a pure function so the backend can recompute after any CRUD
change to detections, wire runs, or boxes.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

from takeoff_engine.models import Bom, BomLine, Box, Category, Detection, WireRun
from takeoff_engine.pricing import price_source_label

# Map detection taxonomy → price_list item_key.
_SWITCH_KEYS: dict[str, str] = {
    "single_pole": "switch_single_pole",
    "three_way": "switch_three_way",
    "three_way_dimmer": "switch_other",
    "dimmer": "switch_dimmer",
    "fan": "switch_fan",
    "vacancy_sensor": "switch_other",
    "astronomical_timer": "switch_other",
}

_RECEPTACLE_KEYS: dict[str, str] = {
    "duplex": "receptacle_duplex",
    "gfci": "receptacle_gfci",
    "gfci_weatherproof": "receptacle_other",
    "afci": "receptacle_other",
    "afci_half_hot": "receptacle_other",
    "gfci_240v": "receptacle_other",
    "gfci_microwave": "receptacle_other",
    "gfci_dishwasher": "receptacle_other",
    "range_hood": "receptacle_other",
    "fan_coil_dedicated": "receptacle_other",
    "240v": "receptacle_other",
}


def _device_item_key(det: Detection) -> str:
    if det.category == Category.SWITCH:
        return _SWITCH_KEYS.get(det.subtype, "switch_other")
    if det.category == Category.RECEPTACLE:
        return _RECEPTACLE_KEYS.get(det.subtype, "receptacle_other")
    if det.category == Category.CEILING_FAN:
        return "device_ceiling_fan"
    if det.category == Category.LIGHT:
        return "device_light"
    if det.category == Category.EXHAUST_FAN:
        return "device_exhaust_fan"
    if det.category == Category.DETECTOR:
        return "device_detector"
    if det.category == Category.JUNCTION_BOX:
        return "device_junction_box"
    return f"device_{det.category.value}"


def _box_item_key(box: Box) -> str | None:
    if box.kind == "none":
        return None
    if box.kind == "fan_rated":
        return "box_fan_rated"
    if box.kind == "ceiling_round":
        return "box_ceiling_round"
    # device boxes by gang count
    if box.gangs <= 1:
        return "box_1gang"
    if box.gangs == 2:
        return "box_2gang"
    if box.gangs == 3:
        return "box_3gang"
    # 4+ gangs: still use 3-gang key as closest listed SKU (noted in docs).
    return "box_3gang"


def _cover_item_key(box: Box) -> str | None:
    if box.cover == "none":
        return None
    if box.cover == "weatherproof_cover":
        return "weatherproof_cover"
    if box.gangs <= 1:
        return "plate_1gang"
    if box.gangs == 2:
        return "plate_2gang"
    return "plate_3gang"


def _lookup(prices: dict[str, Any], key: str) -> dict[str, Any] | None:
    entry = prices.get(key)
    return entry if isinstance(entry, dict) else None


def _line(
    item_key: str,
    description: str,
    quantity: float,
    unit: str,
    prices: dict[str, Any],
    source_ids: list[str],
) -> BomLine:
    entry = _lookup(prices, item_key)
    unit_price = None
    if entry is not None and entry.get("unit_price") is not None:
        unit_price = float(entry["unit_price"])
    extended = None if unit_price is None else round(unit_price * quantity, 2)
    desc = description
    if entry and entry.get("description"):
        desc = str(entry["description"])
    return BomLine(
        item_key=item_key,
        description=desc,
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        extended_price=extended,
        price_source=price_source_label(entry),
        source_ids=sorted(set(source_ids)),
    )


def _assumptions_public(assumptions: dict[str, Any]) -> dict[str, float | str]:
    """Subset of assumptions safe/useful to store on Bom (for UI)."""
    keys = (
        "ceiling_height_ft",
        "switch_height_in",
        "slack_ft_per_end",
        "waste_fraction",
        "cable_roll_ft",
        "dash_length_pt_median",
        "gap_pt_median",
    )
    out: dict[str, float | str] = {}
    for k in keys:
        if k in assumptions:
            v = assumptions[k]
            if isinstance(v, (int, float)):
                out[k] = float(v)
            else:
                out[k] = str(v)
    out.setdefault(
        "routing_note",
        "Dashed plan lines show connectivity, not the true cable route.",
    )
    return out


def compute_bom(
    sheet_id: str,
    detections: list[Detection],
    wire_runs: list[WireRun],
    boxes: list[Box],
    prices: dict[str, Any],
    assumptions: dict[str, Any],
) -> Bom:
    """Build priced BOM lines from detections, wire runs, and boxes.

    Includes:
    - devices (by category/subtype item_key)
    - boxes (by kind / gang)
    - plates / weatherproof covers
    - cable by type: total feet (with waste) and roll count

    Each line carries ``source_ids`` pointing at the detection / box / wire ids
    behind it. Deleted detections are ignored. ``total_usd`` sums only lines
    with a known ``extended_price``.
    """
    active = [d for d in detections if d.status == "active"]
    waste = float(assumptions.get("waste_fraction", 0.10))
    roll_ft = float(assumptions.get("cable_roll_ft", 250))

    lines: list[BomLine] = []

    # --- Devices ---
    device_groups: dict[str, list[Detection]] = defaultdict(list)
    for det in active:
        device_groups[_device_item_key(det)].append(det)
    for key, dets in sorted(device_groups.items()):
        lines.append(
            _line(
                key,
                key.replace("_", " "),
                float(len(dets)),
                "ea",
                prices,
                [d.id for d in dets],
            )
        )

    # --- Boxes ---
    box_groups: dict[str, list[Box]] = defaultdict(list)
    for box in boxes:
        bk = _box_item_key(box)
        if bk is None:
            continue
        box_groups[bk].append(box)
    for key, group in sorted(box_groups.items()):
        lines.append(
            _line(
                key,
                key.replace("_", " "),
                float(len(group)),
                "ea",
                prices,
                [b.id for b in group],
            )
        )

    # --- Covers / plates ---
    cover_groups: dict[str, list[Box]] = defaultdict(list)
    for box in boxes:
        ck = _cover_item_key(box)
        if ck is None:
            continue
        cover_groups[ck].append(box)
    for key, group in sorted(cover_groups.items()):
        lines.append(
            _line(
                key,
                key.replace("_", " "),
                float(len(group)),
                "ea",
                prices,
                [b.id for b in group],
            )
        )

    # --- Cable by type (feet with waste + rolls) ---
    cable_ft: dict[str, float] = defaultdict(float)
    cable_ids: dict[str, list[str]] = defaultdict(list)
    for wr in wire_runs:
        cable_ft[wr.cable_type] += float(wr.total_length_ft)
        cable_ids[wr.cable_type].append(wr.id)

    for cable_type in ("nm_14_2", "nm_14_3"):
        raw_ft = cable_ft.get(cable_type, 0.0)
        if raw_ft <= 0:
            continue
        with_waste = raw_ft * (1.0 + waste)
        roll_key = f"{cable_type}_roll_250"
        # Feet line (informational quantity; priced via rolls).
        lines.append(
            BomLine(
                item_key=f"{cable_type}_ft",
                description=f"{cable_type.replace('_', ' ').upper()} cable (plan + vertical + {int(waste * 100)}% waste)",
                quantity=round(with_waste, 2),
                unit="ft",
                unit_price=None,
                extended_price=None,
                price_source=None,
                source_ids=sorted(set(cable_ids[cable_type])),
            )
        )
        n_rolls = int(math.ceil(with_waste / roll_ft)) if with_waste > 0 else 0
        if n_rolls > 0:
            lines.append(
                _line(
                    roll_key,
                    f"{cable_type} roll",
                    float(n_rolls),
                    "roll",
                    prices,
                    cable_ids[cable_type],
                )
            )

    total = 0.0
    for line in lines:
        if line.extended_price is not None:
            total += line.extended_price

    return Bom(
        sheet_id=sheet_id,
        lines=lines,
        total_usd=round(total, 2),
        assumptions=_assumptions_public(assumptions),
    )
