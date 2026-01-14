from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests

# CLOB public client (official library referenced in docs)
# pip install py-clob-client
from py_clob_client.client import ClobClient


@dataclass
class GammaMarket:
    market_id: str
    slug: str
    question: str
    active: bool
    closed: bool
    end_date_iso: Optional[str]
    clob_token_ids: List[str]
    raw: Dict[str, Any]


class GammaClient:
    def __init__(self, host: str = "https://gamma-api.polymarket.com", timeout_s: int = 15):
        self.host = host.rstrip("/")
        self.timeout_s = timeout_s

    def get_markets(self, limit: int = 200, offset: int = 0, **params: Any) -> List[GammaMarket]:
        """
        Pulls markets from Gamma API.
        Gamma API is documented as a public read-only REST API. :contentReference[oaicite:5]{index=5}
        """
        url = f"{self.host}/markets"
        p = {"limit": limit, "offset": offset, **params}
        r = requests.get(url, params=p, timeout=self.timeout_s)
        r.raise_for_status()
        data = r.json()

        out: List[GammaMarket] = []
        for m in data:
            clob_token_ids = m.get("clobTokenIds") or m.get("clob_token_ids") or []
            out.append(
                GammaMarket(
                    market_id=str(m.get("id", "")),
                    slug=str(m.get("slug", "")),
                    question=str(m.get("question", "")),
                    active=bool(m.get("active", False)),
                    closed=bool(m.get("closed", False)),
                    end_date_iso=m.get("endDateIso") or m.get("end_date_iso"),
                    clob_token_ids=[str(x) for x in clob_token_ids],
                    raw=m,
                )
            )
        return out


class ClobPublic:
    """
    Wrapper around the CLOB public methods exposed by the official client.
    Public methods include get_order_book, get_midpoint, get_spread, etc. :contentReference[oaicite:6]{index=6}
    """
    def __init__(self, host: str = "https://clob.polymarket.com", chain_id: int = 137):
        self.client = ClobClient(host=host, chain_id=chain_id)

    def get_order_book(self, token_id: str) -> Dict[str, Any]:
        return self.client.get_order_book(token_id)

    def get_midpoint(self, token_id: str) -> float:
        resp = self.client.get_midpoint(token_id)
        return float(resp["mid"])

    def get_spread(self, token_id: str) -> float:
        resp = self.client.get_spread(token_id)
        return float(resp["spread"])
