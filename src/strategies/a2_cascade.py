from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class A2State:
    last_mid: Optional[float] = None
    last_spread: Optional[float] = None
    last_depth5: Optional[float] = None


@dataclass(frozen=True)
class A2Params:
    spread_mult: float = 2.0
    depth_collapse: float = 0.60
    sigma_k: float = 2.0


@dataclass(frozen=True)
class A2Signal:
    fired: bool
    direction: Optional[str] = None
    strength: float = 0.0
    details: str = ""


def a2_detect(
    curr_mid: Optional[float],
    curr_spread: Optional[float],
    curr_depth5: Optional[float],
    med_spread: Optional[float],
    med_depth5: Optional[float],
    state: A2State,
    p: A2Params,
) -> A2Signal:
    """
    Simplified A2 cascade detection.
    Checks for spread expansion, depth collapse, and mid jumps.
    """
    if curr_mid is None or curr_spread is None or curr_depth5 is None:
        return A2Signal(fired=False, details="MISSING_DATA")
    
    if med_spread is None or med_depth5 is None:
        return A2Signal(fired=False, details="INSUFFICIENT_HISTORY")
    
    reasons = []
    conds = 0
    
    # 1) Spread expansion
    if med_spread > 0 and curr_spread >= p.spread_mult * med_spread:
        conds += 1
        reasons.append("SPREAD_EXPANSION")
    
    # 2) Depth collapse
    if med_depth5 > 0 and curr_depth5 <= p.depth_collapse * med_depth5:
        conds += 1
        reasons.append("DEPTH_COLLAPSE")
    
    # 3) Mid jump (if we have previous mid)
    if state.last_mid is not None:
        dmid = abs(curr_mid - state.last_mid)
        # Simple heuristic: if mid moved significantly relative to spread
        if curr_spread > 0 and dmid >= p.sigma_k * curr_spread:
            conds += 1
            reasons.append("MID_JUMP")
    
    is_cascade = conds >= 2  # Require at least 2 conditions
    
    if not is_cascade:
        return A2Signal(fired=False, details=",".join(reasons) if reasons else "NO_CASCADE")
    
    # Direction: if mid rose, fade up (short); if fell, fade down (long)
    direction = None
    if state.last_mid is not None:
        direction = "FADE_UP" if (curr_mid - state.last_mid) > 0 else "FADE_DOWN"
    
    strength = min(1.0, conds / 3.0)  # Normalize strength
    
    return A2Signal(
        fired=True,
        direction=direction,
        strength=strength,
        details=",".join(reasons)
    )
