from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


StrategyFamily = Literal["A", "H"]  # A: automatizado/microestructura, H: humano/informacional


@dataclass(frozen=True)
class FrameworkConfig:
    # --- Capital & sizing ---
    equity: float                      # capital asignado al framework (USDC)
    target_pos_frac: float = 0.01      # p (por defecto 1%)
    max_pos_frac: float = 0.05         # cap por mercado (5%)

    # --- Exit model ---
    # alpha: % de Vol24h que estás dispuesto a ser para salir sin castigar el precio
    alpha_exit_A: float = 0.05         # A*: conservador
    alpha_exit_H: float = 0.10         # H*: más laxo
    horizon_exit_days_A: float = 2.0   # días para salir "ordenadamente"
    horizon_exit_days_H: float = 5.0

    # --- Screening thresholds expressed as multiples of S (= target position size) ---
    depth5_min_mult_A: float = 8.0
    vol24h_min_mult_A: float = 20.0
    depth5_min_mult_H: float = 3.0
    vol24h_min_mult_H: float = 10.0

    # --- ExitRisk thresholds ---
    exit_risk_max_A: float = 0.10
    exit_risk_warn_A: float = 0.05
    exit_risk_max_H: float = 0.20
    exit_risk_warn_H: float = 0.10

    # --- A2 detector parameters ---
    a2_window_s: int = 60
    a2_spread_mult: float = 2.0
    a2_depth_collapse_mult: float = 0.60
    a2_jump_sigma_mult: float = 2.0
    a2_pmwv_percentile: float = 0.95

    # --- General ---
    chain_id: int = 137
    clob_host: str = "https://clob.polymarket.com"
    gamma_host: str = "https://gamma-api.polymarket.com"

    def target_position_size(self) -> float:
        return self.equity * self.target_pos_frac

    def max_position_size(self) -> float:
        return self.equity * self.max_pos_frac
