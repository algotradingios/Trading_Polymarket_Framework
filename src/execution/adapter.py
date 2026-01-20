from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class OrderIntent:
    token_id: str
    side: str      # "BUY" or "SELL"
    price: float
    size: float
    reason: str
    strategy: str

class ExecutionAdapter:
    """
    Execution layer placeholder.

    In research mode, we do NOT place any orders.
    When enabled in a permitted environment, implement place_order() using authenticated CLOB calls.
    """
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def place_order(self, intent: OrderIntent) -> Optional[str]:
        if not self.enabled:
            # research mode: no-op
            return None
        raise NotImplementedError("Execution is disabled or not implemented. Keep EXECUTION_ENABLED=False in research mode.")
