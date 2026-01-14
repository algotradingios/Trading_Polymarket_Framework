from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class A2Inputs:
    spread_now: float
    spread_med: float
    depth5_now: float
    depth5_med: float
    mid_now: float
    mid_prev: float
    vol_window: float                 # executed vol in the short window
    sigma_mid_30m: float              # std(mid) over 30m
    pmwv_history: np.ndarray          # history of PMWV values for percentile


@dataclass
class A2Signal:
    is_cascade: bool
    direction: Optional[str]          # "FADE_UP" / "FADE_DOWN" / None
    reasons: str


class A2CascadeDetector:
    def __init__(
        self,
        spread_mult: float = 2.0,
        depth_collapse_mult: float = 0.60,
        jump_sigma_mult: float = 2.0,
        pmwv_percentile: float = 0.95,
    ):
        self.spread_mult = spread_mult
        self.depth_collapse_mult = depth_collapse_mult
        self.jump_sigma_mult = jump_sigma_mult
        self.pmwv_percentile = pmwv_percentile

    def detect(self, x: A2Inputs) -> A2Signal:
        reasons = []
        conds = 0

        # 1) Spread expansion
        if x.spread_med > 0 and x.spread_now >= self.spread_mult * x.spread_med:
            conds += 1
            reasons.append("SPREAD_EXPANSION")

        # 2) Depth collapse
        if x.depth5_med > 0 and x.depth5_now <= self.depth_collapse_mult * x.depth5_med:
            conds += 1
            reasons.append("DEPTH_COLLAPSE")

        # 3) Mid jump
        dmid = abs(x.mid_now - x.mid_prev)
        if x.sigma_mid_30m > 0 and dmid >= self.jump_sigma_mult * x.sigma_mid_30m:
            conds += 1
            reasons.append("MID_JUMP")

        # 4) PMWV extreme
        pmwv = dmid / max(x.vol_window, 1e-9)
        if x.pmwv_history.size >= 30:
            thresh = float(np.quantile(x.pmwv_history, self.pmwv_percentile))
            if pmwv >= thresh:
                conds += 1
                reasons.append("PMWV_EXTREME")

        is_cascade = conds >= 3
        if not is_cascade:
            return A2Signal(False, None, ",".join(reasons))

        # Direction: if mid rose, fade up (short); if fell, fade down (long)
        direction = "FADE_UP" if (x.mid_now - x.mid_prev) > 0 else "FADE_DOWN"
        return A2Signal(True, direction, ",".join(reasons))
