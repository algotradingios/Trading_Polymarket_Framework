from __future__ import annotations

from typing import List, Optional
import math

from config import FrameworkConfig
from data_clients import GammaClient, ClobPublic
from microstructure import depth5_notional, best_bid_ask
from screening import ScreeningEngine, MarketSnapshot


def main() -> None:
    cfg = FrameworkConfig(equity=10_000.0, target_pos_frac=0.01)  # ejemplo
    gamma = GammaClient(cfg.gamma_host)
    clob = ClobPublic(cfg.clob_host, cfg.chain_id)
    screen = ScreeningEngine(cfg)

    # 1) Pull a page of markets
    markets = gamma.get_markets(limit=50, offset=0, active=True)
    # 2) For each market, pick a token_id (ej. YES token_id) and build snapshot
    for m in markets:
        if not m.clob_token_ids:
            continue
        token_id = m.clob_token_ids[0]  # simplificación: primer outcome
        try:
            ob = clob.get_order_book(token_id)
            bid5, ask5, d5 = depth5_notional(ob, k=5)
            spread = clob.get_spread(token_id)
            mid = clob.get_midpoint(token_id)
        except Exception:
            continue

        # Vol24h: si Gamma lo expone, m.raw suele incluirlo; si no, queda None (V1 lo resolvemos)
        vol24h = None
        for key in ["volume24hr", "volume24h", "volume", "volumeUsd"]:
            if key in m.raw and m.raw[key] is not None:
                try:
                    vol24h = float(m.raw[key])
                    break
                except Exception:
                    pass

        snap = MarketSnapshot(token_id=token_id, vol24h=vol24h, depth5=d5, spread=spread, mid=mid)

        # En V0 decidimos familia “tentativa” por heurística:
        # - si spread muy bajo y depth alto -> A; si spread alto/vol bajo -> H
        family = "A" if (spread <= 0.02 and d5 >= cfg.target_position_size() * 10) else "H"

        res = screen.screen(snap, family=family)
        if res.ok:
            print(f"[OK] {m.slug} fam={family} token={token_id} depth5={d5:.0f} vol24h={vol24h} exitRisk={res.exit_risk}")
        else:
            print(f"[NO] {m.slug} fam={family} reason={res.reason}")

if __name__ == "__main__":
    main()
