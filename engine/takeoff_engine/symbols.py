"""Symbol candidate clustering inside the electrical viewport (owned by Agente 2)."""

from __future__ import annotations

from takeoff_engine.models import BBox
from takeoff_engine.types import Candidate, PageContext


def find_candidates(ctx: PageContext, viewport: BBox) -> list[Candidate]:
    """Cluster black segments/fills into symbol candidates inside the viewport.

    Removes wall outlines, dashed wiring chains, and keynote tags first.
    """
    raise NotImplementedError("Agente 2: implement find_candidates")
