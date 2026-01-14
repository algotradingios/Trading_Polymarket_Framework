from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
from collections import Counter, defaultdict



import requests
from py_clob_client.client import ClobClient


# -----------------------------
# Domain objects
# -----------------------------

@dataclass(frozen=True)
class MarketMeta:
    market_id: str
    slug: str
    question: str
    active: bool
    closed: bool
    archived: bool
    restricted: bool
    end_date_iso: Optional[str]
    clob_token_ids: List[str]          # outcome token ids (typically YES/NO for binary)
    volume24h: Optional[float]
    volume: Optional[float]
    liquidity: Optional[float]
    raw: Dict[str, Any]


@dataclass(frozen=True)
class OrderBookTopK:
    token_id: str
    bids: List[Dict[str, str]]
    asks: List[Dict[str, str]]


@dataclass(frozen=True)
class MarketSnapshot:
    market_id: str
    slug: str
    token_id: str
    vol24h: Optional[float]   # from Gamma
    liquidity: Optional[float]
    spread: Optional[float]   # from CLOB
    mid: Optional[float]      # from CLOB
    depth5: Optional[float]   # proxy notional from CLOB book (top 5 levels)
    ok_clob: bool             # whether we could read book/mid/spread


# -----------------------------
# Helpers
# -----------------------------

def _parse_maybe_json_list(v: Any) -> List[str]:
    """
    Gamma sometimes returns clobTokenIds as a list, and sometimes as a JSON-encoded string.
    This normalizes both cases.
    """
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None]
    if isinstance(v, str):
        s = v.strip()
        # common: '["...","..."]'
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(x) for x in arr if x is not None]
            except Exception:
                return []
    return []

def _parse_maybe_json_list_of_dicts(v: Any) -> List[Dict[str, Any]]:
    """
    Gamma sometimes returns nested arrays (like event['markets']) as:
    - a Python list of dicts
    - a JSON-encoded string representing a list of dicts
    """
    if v is None:
        return []
    if isinstance(v, list):
        return [x for x in v if isinstance(x, dict)]
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [x for x in arr if isinstance(x, dict)]
            except Exception:
                return []
    return []

def _parse_market_ids_list(v: Any) -> List[str]:
    """
    Accept list of ids (int/str) or JSON-encoded list. Return list[str].
    """
    if v is None:
        return []
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, (int, str)):
                out.append(str(x))
        return out
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("[") and s.endswith("]"):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(x) for x in arr if isinstance(x, (int, str))]
            except Exception:
                return []
    return []

def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None


def depth5_notional_proxy(ob: Dict[str, Any], k: int = 5) -> float:
    """
    Proxy: sum(price*size) across top-k on both sides.
    Note: good enough for ranking/screening; later we can refine notional semantics if needed.
    """
    def sum_side(levels: List[Dict[str, str]]) -> float:
        s = 0.0
        for lvl in (levels or [])[:k]:
            try:
                px = float(lvl["price"])
                sz = float(lvl["size"])
                s += px * sz
            except Exception:
                continue
        return s

    bids = ob.get("bids", []) or []
    asks = ob.get("asks", []) or []
    return sum_side(bids) + sum_side(asks)


# -----------------------------
# Gamma client
# -----------------------------

class GammaClient:
    def __init__(self, host: str = "https://gamma-api.polymarket.com", timeout_s: int = 20):
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

    def get_markets(self, limit: int = 200, offset: int = 0, **params: Any) -> List[Dict[str, Any]]:
        url = f"{self.host}/markets"
        p = {"limit": limit, "offset": offset, **params}
        r = requests.get(url, params=p, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected Gamma response type: {type(data)}")
        return data

    def iter_markets(
        self,
        pages: int,
        limit: int,
        params: Dict[str, Any],
    ) -> Iterable[Dict[str, Any]]:
        for page in range(pages):
            offset = page * limit
            batch = self.get_markets(limit=limit, offset=offset, **params)
            if not batch:
                break
            for m in batch:
                yield m
    
    def get_events(self, limit: int, offset: int, **params: Any) -> List[Dict[str, Any]]:
        url = f"{self.host}/events"
        p = {"limit": limit, "offset": offset, **params}
        r = requests.get(url, params=p, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected Gamma /events response type: {type(data)}")
        return data

    def iter_events(
        self,
        pages: int,
        limit: int,
        params: Dict[str, Any],
    ) -> Iterable[Dict[str, Any]]:
        for page in range(pages):
            offset = page * limit
            batch = self.get_events(limit=limit, offset=offset, **params)
            if not batch:
                break
            for e in batch:
                yield e

    def get_market_by_id(self, market_id: str) -> Dict[str, Any]:
        url = f"{self.host}/markets/{market_id}"
        r = requests.get(url, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise ValueError(f"Unexpected Gamma /markets/{{id}} response type: {type(data)}")
        return data


# -----------------------------
# CLOB public wrapper with retries/backoff
# -----------------------------

class ClobPublic:
    def __init__(self, host: str = "https://clob.polymarket.com", chain_id: int = 137):
        self.client = ClobClient(host=host, chain_id=chain_id)

    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        return self.client.get_order_book(token_id)

    def get_midpoint(self, token_id: str) -> Optional[float]:
        try:
            resp = self.client.get_midpoint(token_id)
            return float(resp["mid"])
        except Exception:
            return None

    def get_spread(self, token_id: str) -> Optional[float]:
        try:
            resp = self.client.get_spread(token_id)
            return float(resp["spread"])
        except Exception:
            return None


def with_retries(fn, *, retries: int = 3, base_sleep: float = 0.15):
    for i in range(retries):
        try:
            return fn()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(base_sleep * (2 ** i))


# -----------------------------
# MarketDataProvider
# -----------------------------

class MarketDataProvider:
    """
    V0.1 Provider:
    - Gets market metadata from Gamma
    - Validates that token ids are parseable
    - Tries to read CLOB book/mid/spread with retries
    """

    def __init__(
        self,
        gamma_host: str = "https://gamma-api.polymarket.com",
        clob_host: str = "https://clob.polymarket.com",
        chain_id: int = 137,
        timeout_s: int = 20,
    ):
        self.gamma = GammaClient(gamma_host, timeout_s=timeout_s)
        self.clob = ClobPublic(clob_host, chain_id=chain_id)

    def parse_meta(self, m: Dict[str, Any]) -> MarketMeta:
        clob_ids = []
        for k in ("clobTokenIds", "clobTokenIDs", "clob_token_ids", "tokenIds", "token_ids"):
            clob_ids = _parse_maybe_json_list(m.get(k))
            if clob_ids:
                break


        return MarketMeta(
            market_id=str(m.get("id", "")),
            slug=str(m.get("slug", "")),
            question=str(m.get("question", "")),
            active=bool(m.get("active", False)),
            closed=bool(m.get("closed", False)),
            archived=bool(m.get("archived", False)),
            restricted=bool(m.get("restricted", False)),
            end_date_iso=m.get("endDateIso") or m.get("end_date_iso"),
            clob_token_ids=clob_ids,
            volume24h=_to_float(m.get("volume24hr")),
            volume=_to_float(m.get("volume")),
            liquidity=_to_float(m.get("liquidityNum") or m.get("liquidity")),
            raw=m,
        )

    def list_open_markets_universe(
        self,
        pages: int = 10,
        limit: int = 100,
        order: str = "volume24hr",
        ascending: bool = False,
        only_open: bool = True,
        allow_restricted: bool = True,
        require_tokens: bool = True,
    ):
        """
        Stable universe builder API used by run scripts.

        NOTE: We do NOT rely on Gamma's query param `restricted=false` because we observed it being ignored
        in the Spain/EU environment. We fetch open markets and apply restriction filtering locally.
        """
        # If you already have a method that does this (e.g., list_open_unrestricted_markets or similar),
        # forward to it. Otherwise, implement inline.
        params = {
            "active": True,
            "closed": False,
            "archived": False,
            "order": order,
            "ascending": ascending,
        }

        out = []
        seen = set()

        for raw in self.gamma.iter_markets(pages=pages, limit=limit, params=params):
            meta = self.parse_meta(raw)

            if meta.market_id in seen:
                continue
            seen.add(meta.market_id)

            if only_open and (meta.closed or meta.archived):
                continue

            if (not allow_restricted) and meta.restricted:
                continue

            if require_tokens and (not meta.clob_token_ids):
                continue

            out.append(meta)

        return out


    def fetch_snapshot(
        self,
        meta: MarketMeta,
        token_index: int = 0,
        depth_k: int = 5,
        retries: int = 3,
        prefer_liquid_token: bool = True,
    ) -> MarketSnapshot:
        if prefer_liquid_token:
            token_id, ok, d5 = self.pick_best_token_by_depth(meta, depth_k=depth_k, retries=retries)
            ok_clob = ok
            depth5 = d5
        else:
            token_id = meta.clob_token_ids[token_index]
            ok_clob = False
            depth5 = None
            try:
                ob = with_retries(lambda: self.clob.get_order_book(token_id), retries=retries)
                depth5 = depth5_notional_proxy(ob, k=depth_k)
                ok_clob = True
            except Exception:
                ok_clob = False

        spread = None
        mid = None
        if ok_clob:
            try:
                spread = with_retries(lambda: self.clob.get_spread(token_id), retries=retries)
            except Exception:
                spread = None
            try:
                mid = with_retries(lambda: self.clob.get_midpoint(token_id), retries=retries)
            except Exception:
                mid = None

        return MarketSnapshot(
            market_id=meta.market_id,
            slug=meta.slug,
            token_id=token_id,
            vol24h=meta.volume24h,
            liquidity=meta.liquidity,
            spread=spread,
            mid=mid,
            depth5=depth5,
            ok_clob=ok_clob,
        )

    def pick_best_token_by_depth(
        self,
        meta: MarketMeta,
        depth_k: int = 5,
        retries: int = 3,
    ) -> Tuple[str, bool, Optional[float]]:
        best = (None, False, None)  # token_id, ok, depth5
        for token_id in meta.clob_token_ids[:4]:  # normalmente 2; limit defensivo
            try:
                ob = with_retries(lambda: self.clob.get_order_book(token_id), retries=retries)
                d5 = depth5_notional_proxy(ob, k=depth_k)
                if best[2] is None or d5 > best[2]:
                    best = (token_id, True, d5)
            except Exception:
                continue
        if best[0] is None:
            return meta.clob_token_ids[0], False, None
        return best  # type: ignore

    