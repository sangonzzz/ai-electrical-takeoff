"""Safety rules for applying LLM adjudications."""

from __future__ import annotations

from takeoff_engine.llm.apply import apply_adjudications, has_strong_evidence
from takeoff_engine.models import BBox, Category, Detection, Evidence, Point
from takeoff_engine.types import Adjudication


def _det(
    *,
    id: str = "d1",
    category: Category = Category.RECEPTACLE,
    subtype: str = "gfci_240v",
    codes: list[str] | None = None,
    match: float | None = 0.9,
    tokens: list[str] | None = None,
) -> Detection:
    return Detection(
        id=id,
        sheet_id="s",
        category=category,
        subtype=subtype,
        codes=codes or [],
        center=Point(x=1, y=2),
        bbox=BBox(x0=0, y0=0, x1=2, y1=2),
        confidence=0.8,
        source="geometry",
        evidence=Evidence(match_score=match, text_tokens=tokens or []),
    )


def test_strong_evidence_match_or_codes() -> None:
    assert has_strong_evidence(_det(match=0.85, codes=[]))
    assert has_strong_evidence(_det(match=0.2, codes=["240V", "GFI"]))
    assert has_strong_evidence(_det(match=0.2, codes=[], tokens=["GFI"]))
    assert not has_strong_evidence(_det(match=0.3, codes=[], tokens=[]))


def test_flag_only_never_deletes_or_relabels() -> None:
    det = _det(codes=["240V", "GFI"], match=1.0)
    adjs = [
        Adjudication(
            candidate_id="d1",
            label="not_a_component",
            confidence=0.95,
            reason="looks like wiring",
        )
    ]
    out = apply_adjudications([det], adjs, mode="flag_only")
    assert len(out) == 1
    assert out[0].category == Category.RECEPTACLE
    assert out[0].subtype == "gfci_240v"
    assert out[0].needs_review is True
    assert out[0].evidence.llm_label == "not_a_component"


def test_flag_only_never_creates() -> None:
    det = _det(id="keep")
    adjs = [
        Adjudication(
            candidate_id="unknown",
            label="exhaust_fan.bath_exhaust",
            confidence=0.9,
            reason="hallucinated",
        )
    ]
    out = apply_adjudications([det], adjs, mode="flag_only")
    assert len(out) == 1
    assert out[0].id == "keep"
    assert out[0].category == Category.RECEPTACLE


def test_safe_relabel_protects_strong_from_delete_and_category_change() -> None:
    strong = _det(codes=["GFI"], match=0.95, subtype="gfci")
    adjs = [
        Adjudication(
            candidate_id="d1",
            label="exhaust_fan.bath_exhaust",
            confidence=0.9,
            reason="wrong",
        )
    ]
    out = apply_adjudications([strong], adjs, mode="safe_relabel")
    assert len(out) == 1
    assert out[0].category == Category.RECEPTACLE
    assert out[0].needs_review is True

    adjs2 = [
        Adjudication(
            candidate_id="d1",
            label="not_a_component",
            confidence=0.99,
            reason="delete me",
        )
    ]
    out2 = apply_adjudications([strong], adjs2, mode="safe_relabel")
    assert len(out2) == 1


def test_safe_relabel_allows_subtype_on_strong() -> None:
    strong = _det(codes=["GFI"], match=0.95, subtype="gfci")
    adjs = [
        Adjudication(
            candidate_id="d1",
            label="receptacle.gfci_240v",
            confidence=0.9,
            reason="has 240V",
        )
    ]
    out = apply_adjudications([strong], adjs, mode="safe_relabel")
    assert len(out) == 1
    assert out[0].subtype == "gfci_240v"
    assert out[0].category == Category.RECEPTACLE


def test_safe_relabel_may_drop_weak_not_a_component() -> None:
    weak = _det(match=0.3, codes=[], subtype="duplex")
    adjs = [
        Adjudication(
            candidate_id="d1",
            label="not_a_component",
            confidence=0.9,
            reason="noise",
        )
    ]
    out = apply_adjudications([weak], adjs, mode="safe_relabel", warnings=[])
    assert out == []
