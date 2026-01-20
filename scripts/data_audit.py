from __future__ import annotations

import sys
from pathlib import Path
import argparse
import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import SETTINGS
from src.data.clients import GammaClient, ClobPublic
from src.data.clients import depth5_notional_proxy


# -----------------------------
# Audit logic
# -----------------------------

VOL_KEYS_CANDIDATES = [
    "volume24hr", "volume24h", "volume_24h", "volumeUsd24h",
    "volume", "volumeUsd", "volume_usd",
]

TOKEN_KEYS_CANDIDATES = [
    "clobTokenIds", "clob_token_ids", "tokenIds", "token_ids"
]


@dataclass
class AuditConfig:
    gamma_host: str
    clob_host: str
    chain_id: int
    pages: int
    limit: int
    active_only: bool
    sleep_s: float
    topk_depth: int


def extract_token_ids(m: Dict[str, Any]) -> List[str]:
    for k in TOKEN_KEYS_CANDIDATES:
        v = m.get(k)
        if isinstance(v, list) and v:
            return [str(x) for x in v]
        if isinstance(v, str) and v.strip().startswith("["):
            try:
                import json
                arr = json.loads(v)
                if isinstance(arr, list):
                    return [str(x) for x in arr]
            except Exception:
                pass
    return []


def extract_vol24h(m: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """
    Returns (value, key_used)
    """
    for k in VOL_KEYS_CANDIDATES:
        if k in m and m[k] is not None:
            try:
                return float(m[k]), k
            except Exception:
                continue
    return None, None


def safe_str(x: Any, maxlen: int = 110) -> str:
    s = str(x)
    return s if len(s) <= maxlen else s[:maxlen] + "..."


def run_audit(cfg: AuditConfig) -> None:
    gamma = GammaClient(cfg.gamma_host)
    clob = ClobPublic(cfg.clob_host, cfg.chain_id)

    key_freq = Counter()
    vol_key_freq = Counter()
    vol_present = 0
    vol_total = 0
    token_present = 0

    clob_ok_ob = 0
    clob_ok_mid = 0
    clob_ok_spread = 0
    clob_total = 0

    depth5_vals: List[float] = []
    spread_vals: List[float] = []
    mid_vals: List[float] = []

    sample_markets: List[Dict[str, Any]] = []

    for page in range(cfg.pages):
        offset = page * cfg.limit
        params = {}
        if cfg.active_only:
            params["active"] = True

        markets = gamma.get_markets(limit=cfg.limit, offset=offset, **params)

        if not markets:
            break

        for m in markets:
            # record keys
            for k in m.keys():
                key_freq[k] += 1

            tokens = extract_token_ids(m)
            if tokens:
                token_present += 1

            vol, vol_key = extract_vol24h(m)
            vol_total += 1
            if vol is not None:
                vol_present += 1
                vol_key_freq[vol_key] += 1

            # sample a few markets for printing
            if len(sample_markets) < 10:
                sample_markets.append(m)

            # audit CLOB only if token id exists
            if not tokens:
                continue

            token_id = tokens[0]
            clob_total += 1

            try:
                ob = clob.get_order_book(token_id)
                clob_ok_ob += 1
                d5 = depth5_notional_proxy(ob, k=cfg.topk_depth)
                depth5_vals.append(d5)
            except Exception:
                pass

            mid = clob.get_midpoint(token_id)
            if mid is not None:
                clob_ok_mid += 1
                mid_vals.append(mid)

            spr = clob.get_spread(token_id)
            if spr is not None:
                clob_ok_spread += 1
                spread_vals.append(spr)

            if cfg.sleep_s > 0:
                time.sleep(cfg.sleep_s)

    # -----------------------------
    # Reporting
    # -----------------------------
    total_markets_seen = vol_total
    print("\n=== DATA AUDIT SUMMARY ===")
    print(f"Gamma host: {cfg.gamma_host}")
    print(f"CLOB  host: {cfg.clob_host} (chain_id={cfg.chain_id})")
    print(f"Markets fetched: {total_markets_seen}")
    print(f"Markets with token ids: {token_present} ({token_present/max(total_markets_seen,1):.1%})")

    print("\n--- Gamma field availability (top 30 keys) ---")
    for k, c in key_freq.most_common(30):
        print(f"{k:30s}  {c:6d}  ({c/max(total_markets_seen,1):.1%})")

    print("\n--- Vol24h availability ---")
    print(f"Markets with any Vol24h key parsed: {vol_present}/{vol_total} ({vol_present/max(vol_total,1):.1%})")
    if vol_key_freq:
        print("Vol key usage breakdown:")
        for k, c in vol_key_freq.most_common():
            print(f"  {k:20s} {c:6d}")
    else:
        print("No volume keys detected among candidates:", VOL_KEYS_CANDIDATES)

    print("\n--- CLOB access quality (for first token_id per market) ---")
    if clob_total > 0:
        print(f"Order book success: {clob_ok_ob}/{clob_total} ({clob_ok_ob/clob_total:.1%})")
        print(f"Midpoint   success: {clob_ok_mid}/{clob_total} ({clob_ok_mid/clob_total:.1%})")
        print(f"Spread     success: {clob_ok_spread}/{clob_total} ({clob_ok_spread/clob_total:.1%})")
    else:
        print("No token IDs found; CLOB audit skipped.")

    def summarize(arr: List[float], name: str) -> None:
        if not arr:
            print(f"{name}: no data")
            return
        a = np.asarray(arr, dtype=float)
        print(
            f"{name}: n={len(a)} "
            f"p10={np.quantile(a,0.10):.6g} "
            f"p50={np.quantile(a,0.50):.6g} "
            f"p90={np.quantile(a,0.90):.6g} "
            f"max={a.max():.6g}"
        )

    print("\n--- Basic distributions (proxies) ---")
    summarize(depth5_vals, f"Depth{cfg.topk_depth} notional proxy")
    summarize(spread_vals, "Spread")
    summarize(mid_vals, "Midpoint")

    # Print a compact sample of raw markets to inspect schema manually
    print("\n--- Sample market objects (truncated) ---")
    for i, m in enumerate(sample_markets[:5], start=1):
        print(f"\nSample #{i}")
        for k in sorted(m.keys()):
            if k in ("description", "rules", "question"):
                print(f"  {k}: {safe_str(m.get(k))}")
            elif k in VOL_KEYS_CANDIDATES or k in TOKEN_KEYS_CANDIDATES or k in ("id", "slug", "active", "closed", "endDateIso", "end_date_iso"):
                print(f"  {k}: {safe_str(m.get(k))}")

    # Recommendations
    print("\n=== RECOMMENDATIONS ===")
    if vol_present / max(vol_total, 1) < 0.6:
        print("- Vol24h is missing or inconsistent in Gamma for a large fraction of markets.")
        print("  Action: plan V1 integration with a dedicated trades/volume source (Data API or Subgraph).")
    else:
        print("- Vol24h appears sufficiently available in Gamma for V0/V1 screening.")

    if clob_ok_ob / max(clob_total, 1) < 0.9:
        print("- Orderbook fetch fails often. This may impact microstructure strategies (A*).")
        print("  Action: add retries/backoff and consider websocket subscriptions for stability.")
    else:
        print("- CLOB orderbook access looks stable for basic screening.")

    print("- Next step: freeze the schema keys we will trust and formalize a 'MarketDataProvider' interface.")


def parse_args() -> AuditConfig:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gamma-host", default=SETTINGS.GAMMA_HOST)
    ap.add_argument("--clob-host", default=SETTINGS.CLOB_HOST)
    ap.add_argument("--chain-id", type=int, default=SETTINGS.CHAIN_ID)
    ap.add_argument("--pages", type=int, default=2, help="Number of pages to fetch")
    ap.add_argument("--limit", type=int, default=50, help="Markets per page")
    ap.add_argument("--active-only", action="store_true", help="Attempt to filter active markets")
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep between CLOB calls (rate limiting)")
    ap.add_argument("--topk-depth", type=int, default=5, help="Depth K levels for depth proxy")
    a = ap.parse_args()
    return AuditConfig(
        gamma_host=a.gamma_host,
        clob_host=a.clob_host,
        chain_id=a.chain_id,
        pages=a.pages,
        limit=a.limit,
        active_only=a.active_only,
        sleep_s=a.sleep,
        topk_depth=a.topk_depth,
    )


if __name__ == "__main__":
    cfg = parse_args()
    run_audit(cfg)
