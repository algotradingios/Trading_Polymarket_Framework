from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

StrategyFamily = Literal["A", "H"]


@dataclass(frozen=True)
class ScreeningConfig:
    equity: float
    target_pos_frac: float = 0.01
    depth5_min_mult_A: float = 8.0
    vol24h_min_mult_A: float = 20.0
    depth5_min_mult_H: float = 3.0
    vol24h_min_mult_H: float = 10.0
    exit_risk_max_A: float = 0.10
    exit_risk_max_H: float = 0.20


@dataclass(frozen=True)
class ScreeningResult:
    ok: bool
    reason: str
    family: StrategyFamily
    S: float
    exit_risk: Optional[float]
    depth5_min: float
    vol24h_min: float


class ScreeningEngine:
    def __init__(self, cfg: ScreeningConfig):
        self.cfg = cfg

    def S(self) -> float:
        return self.cfg.equity * self.cfg.target_pos_frac

    def screen(
        self,
        *,
        family: StrategyFamily,
        vol24h: Optional[float],
        depth5: Optional[float],
        ok_clob: bool,
    ) -> ScreeningResult:
        S = self.S()

        if family == "A":
            depth5_min = self.cfg.depth5_min_mult_A * S
            vol24h_min = self.cfg.vol24h_min_mult_A * S
            exit_risk_max = self.cfg.exit_risk_max_A
        else:
            depth5_min = self.cfg.depth5_min_mult_H * S
            vol24h_min = self.cfg.vol24h_min_mult_H * S
            exit_risk_max = self.cfg.exit_risk_max_H

        if not ok_clob or depth5 is None:
            return ScreeningResult(False, "NO_CLOB_BOOK", family, S, None, depth5_min, vol24h_min)

        if depth5 < depth5_min:
            return ScreeningResult(False, "DEPTH_TOO_LOW", family, S, None, depth5_min, vol24h_min)

        if vol24h is None:
            # Tu audit dice que volume24hr existe siempre en Gamma, así que si llega None hay bug upstream.
            return ScreeningResult(False, "VOL24H_MISSING", family, S, None, depth5_min, vol24h_min)

        if vol24h < vol24h_min:
            return ScreeningResult(False, "VOL24H_TOO_LOW", family, S, None, depth5_min, vol24h_min)

        exit_risk = S / max(vol24h, 1e-9)
        if exit_risk > exit_risk_max:
            return ScreeningResult(False, "EXIT_RISK_TOO_HIGH", family, S, exit_risk, depth5_min, vol24h_min)

        return ScreeningResult(True, "OK", family, S, exit_risk, depth5_min, vol24h_min)
