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


@dataclass(frozen=True)
class BotScoreInputs:
    mid_move_abs: float
    spread: Optional[float]
    depth5: Optional[float]
    vol24h: float


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


# Simplified interface functions for engine_research.py
def botscore_v0(inputs: BotScoreInputs) -> float:
    """
    Simplified botscore calculation from snapshot inputs.
    Uses PMWV (price movement per unit volume) as proxy.
    """
    if inputs.vol24h <= 0 or inputs.mid_move_abs is None:
        return 0.5  # neutral
    
    pmwv = inputs.mid_move_abs / max(inputs.vol24h, 1e-9)
    
    # Simple heuristic: high PMWV + low spread + high depth = more bot-like
    # This is a simplified version; full version would use percentile ranking
    spread_norm = (inputs.spread or 0.1) / 0.1  # normalize around 0.1
    depth_norm = (inputs.depth5 or 0) / 1000.0  # normalize around 1000
    
    # Higher PMWV = more bot-like
    # Lower spread = more bot-like  
    # Higher depth = more bot-like
    score = min(1.0, max(0.0, 0.3 + pmwv * 0.3 - spread_norm * 0.2 + depth_norm * 0.2))
    return score


def regime_from_score(bot_score: float) -> str:
    """Convert botscore to regime classification."""
    return BotScoreV0.bucket(bot_score)
