"""
Polymarket Quantitative Research Framework

A modular framework for quantitative research on Polymarket prediction markets.
"""

__version__ = "0.1.0"

# Convenience imports
from .config.settings import SETTINGS
from .data.clients import MarketDataProvider
from .data.models import MarketMeta, MarketSnapshot, OrderBookTopK
from .domain.screening import ScreeningConfig, ScreeningEngine, ScreeningResult
from .domain.bot_score import BotScoreInputs, botscore_v0, regime_from_score
from .strategies.a2_cascade import A2State, A2Params, A2Signal, a2_detect
from .strategies.h1_informational import H1Case, H1Decision, H1Checklist
from .storage.store import Store, SnapshotRow, BotScoreRow, SignalRow
from .execution.adapter import ExecutionAdapter, OrderIntent

__all__ = [
    # Config
    "SETTINGS",
    # Data
    "MarketDataProvider",
    "MarketMeta",
    "MarketSnapshot",
    "OrderBookTopK",
    # Domain
    "ScreeningConfig",
    "ScreeningEngine",
    "ScreeningResult",
    "BotScoreInputs",
    "botscore_v0",
    "regime_from_score",
    # Strategies
    "A2State",
    "A2Params",
    "A2Signal",
    "a2_detect",
    "H1Case",
    "H1Decision",
    "H1Checklist",
    # Storage
    "Store",
    "SnapshotRow",
    "BotScoreRow",
    "SignalRow",
    # Execution
    "ExecutionAdapter",
    "OrderIntent",
]
