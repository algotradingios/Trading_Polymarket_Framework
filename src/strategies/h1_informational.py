from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class H1Case:
    market_slug: str
    question: str
    resolution_source_defined: bool
    wording_is_unambiguous: bool
    scenarios: List[Tuple[str, float]]     # (scenario_name, probability)
    p_market: float                        # implied market probability (0..1)
    catalyst_defined: bool
    thesis_invalidation_rule: str


@dataclass
class H1Decision:
    ok: bool
    reason: str
    p_model: Optional[float]
    edge: Optional[float]


class H1Checklist:
    def __init__(self, min_edge: float = 0.10):  # default 10pp edge
        self.min_edge = min_edge

    def evaluate(self, case: H1Case) -> H1Decision:
        # Gate 1: resolution/wording
        if not case.resolution_source_defined:
            return H1Decision(False, "NO_RESOLUTION_SOURCE", None, None)
        if not case.wording_is_unambiguous:
            return H1Decision(False, "WORDING_AMBIGUOUS", None, None)

        # Gate 2: scenario model
        if not case.scenarios:
            return H1Decision(False, "NO_SCENARIOS", None, None)
        total = sum(p for _, p in case.scenarios)
        if total <= 0:
            return H1Decision(False, "INVALID_SCENARIO_PROBS", None, None)

        # normalize if user inputs are not perfectly normalized
        p_model = sum(p for _, p in case.scenarios) / total
        edge = abs(p_model - case.p_market)

        if edge < self.min_edge:
            return H1Decision(False, "EDGE_TOO_SMALL", p_model, edge)

        # Gate 3: plan to get paid
        if not case.catalyst_defined and "resolution" not in case.thesis_invalidation_rule.lower():
            # You can still do it, but this is usually a warning state
            return H1Decision(True, "OK_NO_CATALYST_ASSUME_HOLD", p_model, edge)

        return H1Decision(True, "OK", p_model, edge)
