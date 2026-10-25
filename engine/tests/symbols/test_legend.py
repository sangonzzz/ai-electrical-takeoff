"""Legend extraction tests against Escondido Plan 1 (SPEC §1, §5)."""

from __future__ import annotations

from pathlib import Path

from takeoff_engine.legend import extract_legend, legend_templates, map_description
from takeoff_engine.models import Category
from takeoff_engine.pdf_context import load_page


def test_map_description_core_types() -> None:
    assert map_description("CEILING FAN OPTIONAL (PRE WIRE)")[0] == Category.CEILING_FAN
    assert map_description("RECESSED HIGH- EFFICACY DOWNLIGHT")[1] == "recessed"
    assert map_description("ELECTRICAL SWITCH")[1] == "single_pole"
    assert map_description("DUPLEX OUTLET GROUND FAULT INTERRUPTER")[1] == "gfci"
    assert map_description("COMBINATION SMOKE/CARBON MONOXIDE")[1] == "smoke_co"
    assert map_description("COLD WATER STUB OUT")[3] is True  # exclude
    assert map_description("22\"X30\" MIN. ATTIC ACCESS PANEL")[3] is True


def test_page1_legend_has_required_entries(plans_pdf: Path) -> None:
    ctx = load_page(plans_pdf, 0)
    entries = extract_legend(ctx)
    assert len(entries) >= 25, f"expected >=25 legend entries, got {len(entries)}"

    descs = " | ".join(e.description.upper() for e in entries)

    def has(*needles: str) -> bool:
        return any(n in descs for n in needles)

    assert has("CEILING FAN")
    assert has("DOWNLIGHT")
    assert has("SWITCH")  # single-pole lives under ELECTRICAL SWITCH
    assert has("GROUND FAULT", "GFI") or any(
        e.category == Category.RECEPTACLE and e.subtype == "gfci" for e in entries
    )
    assert has("SMOKE") and (
        has("CARBON", "SMOKE/CARBON", "COMBINATION")
        or any(e.subtype == "smoke_co" for e in entries)
    )

    # Plumbing / attic must not appear as kept entries.
    for e in entries:
        u = e.description.upper()
        assert "ATTIC ACCESS" not in u
        assert "COLD WATER" not in u
        assert "HOSE BIBB" not in u

    templates = legend_templates(ctx, entries)
    assert len(templates) == len(entries)
    # At least some templates carry real vector primitives.
    with_prims = sum(1 for t in templates.values() if t.segments or t.fills)
    assert with_prims >= 15
