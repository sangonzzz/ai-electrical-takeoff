"""Evaluation package: ground truth, metrics, reports, baseline comparison.

Owned by Agente 7. The ``takeoff eval`` CLI (Agente 1) should call::

    from eval.runner import run_eval_from_cli
    run_eval_from_cli(pdf=pdf, out=out)
"""

from __future__ import annotations

__all__ = ["MATCH_RADIUS_PT", "run_eval"]


def __getattr__(name: str):
    if name == "MATCH_RADIUS_PT":
        from eval.metrics import MATCH_RADIUS_PT

        return MATCH_RADIUS_PT
    if name == "run_eval":
        from eval.runner import run_eval

        return run_eval
    raise AttributeError(name)
