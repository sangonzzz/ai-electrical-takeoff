"""Bill of materials aggregation (owned by Agente 8).

``compute_bom`` is a pure function so the backend can recompute after any CRUD
change to detections, wire runs, or boxes.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Literal

from takeoff_engine.models import Bom, BomLine, Box, Category, Detection, WireRun
from takeoff_engine.pricing import price_source_label

BomSection = Literal["devices", "fixtures", "boxes", "cable"]

# Map detection taxonomy → price_list item_key (no catch-all "other" buckets).
_SWITCH_KEYS: dict[str, str] = {
    "single_pole": "switch_single_pole",
    "three_way": "switch_three_way",
    "three_way_dimmer": "switch_three_way_dimmer",
    "dimmer": "switch_dimmer",
    "fan": "switch_fan",
    "vacancy_sensor": "switch_vacancy_sensor",
    "astronomical_timer": "switch_astronomical_timer",
}

_RECEPTACLE_KEYS: dict[str, str] = {
    "duplex": "receptacle_duplex",
    "gfci": "receptacle_gfci",
    "gfci_weatherproof": "receptacle_gfci",
    "gfci_microwave": "receptacle_gfci",
    "gfci_dishwasher": "receptacle_gfci",
    "range_hood": "receptacle_gfci",
    "afci": "receptacle_afci",
    "afci_half_hot": "receptacle_afci",
    "fan_coil_dedicated": "receptacle_afci",
    "gfci_240v": "receptacle_240v",
    "240v": "receptacle_240v",
}

_LIGHT_KEYS: dict[str, str] = {
    "recessed": "device_light_recessed",
    "recessed_vapor_proof": "device_light_recessed",
    "wall": "device_light_wall",
    "exterior_wall": "device_light_exterior",
    "pendant": "device_light_pendant",
}

# Fixture allowance SKUs (fans, lights, exhaust, detectors) — own BOM section.
_FIXTURE_ITEM_KEYS = frozenset(
    {
        "device_ceiling_fan",
        "device_light_recessed",
        "device_light_wall",
        "device_light_exterior",
        "device_light_pendant",
        "device_exhaust_fan",
        "device_detector",
    }
)

_SECTION_ORDER: tuple[BomSection, ...] = ("devices", "fixtures", "boxes", "cable")
_SECTION_LABELS: dict[BomSection, str] = {
    "devices": "Devices",
    "fixtures": "Fixtures (allowance)",
    "boxes": "Boxes and plates",
    "cable": "Cable",
}


def _device_item_key(det: Detection) -> str:
    if det.category == Category.SWITCH:
        return _SWITCH_KEYS.get(det.subtype, f"switch_{det.subtype}")
    if det.category == Category.RECEPTACLE:
        return _RECEPTACLE_KEYS.get(det.subtype, f"receptacle_{det.subtype}")
    if det.category == Category.CEILING_FAN:
        return "device_ceiling_fan"
    if det.category == Category.LIGHT:
        return _LIGHT_KEYS.get(det.subtype, "device_light_pendant")
    if det.category == Category.EXHAUST_FAN:
        return "device_exhaust_fan"
    if det.category == Category.DETECTOR:
        return "device_detector"
    if det.category == Category.JUNCTION_BOX:
        return "device_junction_box"
    return f"device_{det.category.value}"


def bom_section_for_item_key(item_key: str) -> BomSection:
    """Classify a BOM line into Devices / Fixtures / Boxes / Cable.

    WHY: quote PDF and UI need a stable grouping without changing the BomLine
    contract. Fixtures are allowance SKUs (fan/light/exhaust/detector).
    """
    k = item_key.lower()
    if k.startswith("nm_") or k.endswith("_ft") or "cable" in k or k.endswith("_roll_250"):
        return "cable"
    if (
        k.startswith("box_")
        or k.startswith("plate_")
        or k == "weatherproof_cover"
    ):
        return "boxes"
    if item_key in _FIXTURE_ITEM_KEYS or k.startswith("device_light"):
        return "fixtures"
    if k.startswith("device_ceiling_fan") or k.startswith("device_exhaust") or k.startswith(
        "device_detector"
    ):
        return "fixtures"
    return "devices"


def group_bom_lines(
    lines: Iterable[BomLine],
) -> list[tuple[BomSection, str, list[BomLine]]]:
    """Group BOM lines for display/export: (section_key, label, lines).

    Empty sections are omitted. Order is Devices → Fixtures → Boxes → Cable.
    """
    buckets: dict[BomSection, list[BomLine]] = {s: [] for s in _SECTION_ORDER}
    for line in lines:
        buckets[bom_section_for_item_key(line.item_key)].append(line)
    out: list[tuple[BomSection, str, list[BomLine]]] = []
    for section in _SECTION_ORDER:
        group = buckets[section]
        if group:
            out.append((section, _SECTION_LABELS[section], group))
    return out


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
        "pricing_note_240v",
        "pricing_note_detector",
        "pricing_note_fixtures",
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

    Lines are ordered Devices → Fixtures (allowance) → Boxes and plates → Cable
    so quote/UI grouping stays stable without a contract field. Use
    ``group_bom_lines`` for labeled sections.

    Each line carries ``source_ids`` pointing at the detection / box / wire ids
    behind it. Deleted detections are ignored. ``total_usd`` sums only lines
    with a known ``extended_price``.
    """
    active = [d for d in detections if d.status == "active"]
    waste = float(assumptions.get("waste_fraction", 0.10))
    roll_ft = float(assumptions.get("cable_roll_ft", 250))

    device_lines: list[BomLine] = []
    fixture_lines: list[BomLine] = []

    device_groups: dict[str, list[Detection]] = defaultdict(list)
    for det in active:
        device_groups[_device_item_key(det)].append(det)
    for key, dets in sorted(device_groups.items()):
        line = _line(
            key,
            key.replace("_", " "),
            float(len(dets)),
            "ea",
            prices,
            [d.id for d in dets],
        )
        if bom_section_for_item_key(key) == "fixtures":
            fixture_lines.append(line)
        else:
            device_lines.append(line)

    box_lines: list[BomLine] = []
    box_groups: dict[str, list[Box]] = defaultdict(list)
    for box in boxes:
        bk = _box_item_key(box)
        if bk is None:
            continue
        box_groups[bk].append(box)
    for key, group in sorted(box_groups.items()):
        box_lines.append(
            _line(
                key,
                key.replace("_", " "),
                float(len(group)),
                "ea",
                prices,
                [b.id for b in group],
            )
        )

    cover_groups: dict[str, list[Box]] = defaultdict(list)
    for box in boxes:
        ck = _cover_item_key(box)
        if ck is None:
            continue
        cover_groups[ck].append(box)
    for key, group in sorted(cover_groups.items()):
        box_lines.append(
            _line(
                key,
                key.replace("_", " "),
                float(len(group)),
                "ea",
                prices,
                [b.id for b in group],
            )
        )

    cable_lines: list[BomLine] = []
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
        cable_lines.append(
            BomLine(
                item_key=f"{cable_type}_ft",
                description=(
                    f"{cable_type.replace('_', ' ').upper()} cable "
                    f"(plan + vertical + {int(waste * 100)}% waste)"
                ),
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
            cable_lines.append(
                _line(
                    roll_key,
                    f"{cable_type} roll",
                    float(n_rolls),
                    "roll",
                    prices,
                    cable_ids[cable_type],
                )
            )

    lines = device_lines + fixture_lines + box_lines + cable_lines

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


__all__ = [
    "compute_bom",
    "bom_section_for_item_key",
    "group_bom_lines",
    "_device_item_key",
    "_SECTION_LABELS",
]
