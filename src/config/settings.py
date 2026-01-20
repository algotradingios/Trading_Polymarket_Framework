# settings.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:

    # --- Mode toggles ---
    ALLOW_RESTRICTED: bool = True        # Spain/EU: True for research
    EXECUTION_ENABLED: bool = False      # MUST remain False in research mode

    # --- API / polling ---
    GAMMA_HOST: str = "https://gamma-api.polymarket.com"
    CLOB_HOST: str = "https://clob.polymarket.com"
    CHAIN_ID: int = 137
    PAGES: int = 10
    LIMIT: int = 100
    ORDER: str = "volume24hr"
    ASCENDING: bool = False
    SNAPSHOT_SLEEP_S: float = 0.05       # sleep between CLOB calls
    LOOP_SLEEP_S: float = 30.0           # seconds between full cycles
    MAX_MARKETS_PER_CYCLE: int = 80      # hard cap to control rate/latency

    # --- Capital assumptions (screening) ---
    EQUITY: float = 10_000.0
    TARGET_POS_FRAC: float = 0.01

    # --- A2 detector params ---
    A2_WINDOW_S: int = 60
    A2_SPREAD_MULT: float = 2.0
    A2_DEPTH_COLLAPSE: float = 0.60
    A2_SIGMA_K: float = 2.0
    A2_MAX_HOLD_S: int = 3600

    # --- Storage ---
    SQLITE_PATH: str = "research.db"

SETTINGS = Settings()
