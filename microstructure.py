from __future__ import annotations

from typing import Any, Dict, List, Tuple
import math


def _sum_top_levels(levels: List[Dict[str, str]], k: int = 5) -> float:
    """
    levels: [{price: "0.51", size: "123.4"}, ...]
    We interpret 'size' as base quantity; for a quick Depth proxy we use notional ~ price*size.
    If you want USDC depth precisely, refine once we confirm size semantics for each token.
    """
    s = 0.0
    for lvl in levels[:k]:
        px = float(lvl["price"])
        sz = float(lvl["size"])
        s += px * sz
    return s


def depth5_notional(order_book: Dict[str, Any], k: int = 5) -> Tuple[float, float, float]:
    bids = order_book.get("bids", [])
    asks = order_book.get("asks", [])
    bid = _sum_top_levels(bids, k=k)
    ask = _sum_top_levels(asks, k=k)
    return bid, ask, bid + ask


def best_bid_ask(order_book: Dict[str, Any]) -> Tuple[float, float]:
    bids = order_book.get("bids", [])
    asks = order_book.get("asks", [])
    bb = float(bids[0]["price"]) if bids else math.nan
    ba = float(asks[0]["price"]) if asks else math.nan
    return bb, ba


def book_symmetry(depth_bid: float, depth_ask: float, eps: float = 1e-9) -> float:
    """
    1 = perfectly symmetric, 0 = totally one-sided
    """
    return 1.0 - abs(depth_bid - depth_ask) / (depth_bid + depth_ask + eps)
