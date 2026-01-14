from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import numpy as np


@dataclass
class BotFeatures:
    ci_proxy: float   # quote churn proxy
    qtr_proxy: float  # book_changes / trades
    pmwv: float       # |Δmid| / volume
    symmetry: float   # book symmetry (0..1)


def percentile_rank(x: float, ref: List[float]) -> float:
    """
    Returns percentile rank in [0,1].
    """
    if not ref:
        return 0.5
    arr = np.asarray(ref, dtype=float)
    return float((arr < x).mean())


class BotScoreV0:
    def __init__(self, w_ci=0.30, w_qtr=0.25, w_pmwv=0.25, w_sym=0.20):
        self.w_ci = w_ci
        self.w_qtr = w_qtr
        self.w_pmwv = w_pmwv
        self.w_sym = w_sym

    def score(
        self,
        feat: BotFeatures,
        ref_ci: List[float],
        ref_qtr: List[float],
        ref_pmwv: List[float],
        ref_sym: List[float],
    ) -> float:
        # Normalize to percentiles
        ci = percentile_rank(feat.ci_proxy, ref_ci)
        qtr = percentile_rank(feat.qtr_proxy, ref_qtr)
        pmwv = percentile_rank(feat.pmwv, ref_pmwv)
        sym = percentile_rank(feat.symmetry, ref_sym)
        return self.w_ci * ci + self.w_qtr * qtr + self.w_pmwv * pmwv + self.w_sym * sym

    @staticmethod
    def bucket(bot_score: float) -> str:
        if bot_score >= 0.65:
            return "BOT"
        if bot_score <= 0.40:
            return "HUMAN"
        return "MIXED"
