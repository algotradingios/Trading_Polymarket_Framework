# settings.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    # Mode toggles
    ALLOW_RESTRICTED: bool = True      # Spain/EU: True for research
    EXECUTION_ENABLED: bool = False    # always False unless in permitted environment

    # API configuration
    GAMMA_HOST: str = "https://gamma-api.polymarket.com"
    CLOB_HOST: str = "https://clob.polymarket.com"
    CHAIN_ID: int = 137

    # Capital assumptions (used by screening)
    EQUITY: float = 10_000.0
    TARGET_POS_FRAC: float = 0.01

    # Universe fetching
    PAGES: int = 10
    LIMIT: int = 100
    ORDER: str = "volume24hr"
    ASCENDING: bool = False

SETTINGS = Settings()
