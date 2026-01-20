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
    Improved botscore calculation from snapshot inputs.
    
    Bot-like markets exhibit:
    - High price movement per unit volume (PMWV) - bots create volatility
    - Tight spreads relative to price level
    - High depth relative to volume (liquidity provision)
    - Low spread volatility (stable market making)
    
    Human-like markets exhibit:
    - Low PMWV (price moves reflect information, not noise)
    - Wider spreads (less continuous market making)
    - Lower depth/volume ratios
    - More asymmetric order books
    
    Returns score in [0, 1] where:
    - >= 0.65: BOT regime
    - <= 0.40: HUMAN regime  
    - 0.40-0.65: MIXED regime
    """
    if inputs.vol24h <= 0:
        return 0.5  # neutral if no volume
    
    # 1) PMWV component (price movement per unit volume)
    # Higher PMWV = more bot-like (bots create noise/volatility)
    # Use log scale to handle wide range of values
    pmwv = inputs.mid_move_abs / max(inputs.vol24h, 1e-9)
    # Typical range: 0.000001 to 0.1
    # Use sigmoid-like transformation: log(1 + pmwv * 10000) / log(10001)
    pmwv_score = min(1.0, np.log1p(pmwv * 10000) / np.log(10001))
    
    # 2) Spread tightness component
    # Lower spread = more bot-like (market makers keep spreads tight)
    if inputs.spread is None or inputs.spread <= 0:
        spread_score = 0.5  # neutral if no spread data
    else:
        # Typical spreads: 0.001 (tight) to 0.1 (wide)
        # Invert: tight spreads get high scores
        # Use sigmoid: 1 / (1 + spread * 100)
        spread_score = 1.0 / (1.0 + inputs.spread * 100)
    
    # 3) Depth-to-volume ratio component
    # Higher depth/volume = more bot-like (liquidity provision)
    if inputs.depth5 is None or inputs.depth5 <= 0:
        depth_score = 0.3  # lower score if no depth
    else:
        # Depth-to-volume ratio: how much liquidity vs trading activity
        depth_vol_ratio = inputs.depth5 / max(inputs.vol24h, 1e-9)
        # Typical range: 0.01 to 10+
        # Use log scale: log(1 + ratio) / log(11)
        depth_score = min(1.0, np.log1p(depth_vol_ratio) / np.log(11))
    
    # 4) Spread stability proxy (using current spread as indicator)
    # Very tight spreads (< 0.002) suggest active market making (bot-like)
    # Very wide spreads (> 0.05) suggest less market making (human-like)
    if inputs.spread is None:
        stability_score = 0.5
    else:
        if inputs.spread < 0.002:
            stability_score = 1.0  # very tight = bot-like
        elif inputs.spread < 0.01:
            stability_score = 0.7  # tight = somewhat bot-like
        elif inputs.spread < 0.05:
            stability_score = 0.4  # moderate = mixed
        else:
            stability_score = 0.2  # wide = human-like
    
    # Weighted combination
    # PMWV is most important (30%), then spread tightness (25%), depth ratio (25%), stability (20%)
    score = (
        0.30 * pmwv_score +
        0.25 * spread_score +
        0.25 * depth_score +
        0.20 * stability_score
    )
    
    # Ensure score is in [0, 1]
    return float(np.clip(score, 0.0, 1.0))


def regime_from_score(bot_score: float) -> str:
    """Convert botscore to regime classification."""
    return BotScoreV0.bucket(bot_score)
