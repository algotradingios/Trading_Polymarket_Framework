from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Deque, Optional, Tuple

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import SETTINGS
from src.data.clients import MarketDataProvider
from src.domain.screening import ScreeningConfig, ScreeningEngine
from src.domain.bot_score import BotScoreInputs, botscore_v0, regime_from_score
from src.strategies.a2_cascade import A2State, A2Params, a2_detect
from src.storage.store import Store, SnapshotRow, BotScoreRow, SignalRow
from src.execution.adapter import ExecutionAdapter, OrderIntent


@dataclass
class RollingMedians:
    spreads: Deque[float]
    depths: Deque[float]

    def medians(self) -> Tuple[Optional[float], Optional[float]]:
        if not self.spreads or not self.depths:
            return None, None
        ss = sorted(self.spreads)
        dd = sorted(self.depths)
        return ss[len(ss)//2], dd[len(dd)//2]


def main() -> None:
    provider = MarketDataProvider(
        gamma_host=SETTINGS.GAMMA_HOST,
        clob_host=SETTINGS.CLOB_HOST,
        chain_id=SETTINGS.CHAIN_ID,
    )

    store = Store(SETTINGS.SQLITE_PATH)
    execution = ExecutionAdapter(enabled=SETTINGS.EXECUTION_ENABLED)

    screener = ScreeningEngine(
        ScreeningConfig(
            equity=SETTINGS.EQUITY,
            target_pos_frac=SETTINGS.TARGET_POS_FRAC,
        )
    )

    # Per-market rolling state
    last_mid: Dict[str, Optional[float]] = {}
    a2_state: Dict[str, A2State] = {}
    rolling: Dict[str, RollingMedians] = defaultdict(lambda: RollingMedians(deque(maxlen=30), deque(maxlen=30)))

    a2_params = A2Params(
        spread_mult=SETTINGS.A2_SPREAD_MULT,
        depth_collapse=SETTINGS.A2_DEPTH_COLLAPSE,
        sigma_k=SETTINGS.A2_SIGMA_K,
    )

    print("=== Research Engine starting ===")
    print("ALLOW_RESTRICTED =", SETTINGS.ALLOW_RESTRICTED)
    print("EXECUTION_ENABLED =", SETTINGS.EXECUTION_ENABLED)
    print("DB =", SETTINGS.SQLITE_PATH)

    while True:
        cycle_ts = store.now_ts()

        # 1) Universe
        metas = provider.list_open_markets_universe(
            pages=SETTINGS.PAGES,
            limit=SETTINGS.LIMIT,
            order=SETTINGS.ORDER,
            ascending=SETTINGS.ASCENDING,
            only_open=True,
            allow_restricted=SETTINGS.ALLOW_RESTRICTED,
            require_tokens=True,
        )

        # Hard cap per cycle (rate limiting)
        metas = metas[:SETTINGS.MAX_MARKETS_PER_CYCLE]

        print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Universe size: {len(metas)}")

        # 2) Snapshot + Screening + Score + Routing
        ok_count = 0
        a2_fires = 0
        h1_candidates = 0

        for meta in metas:
            snap = provider.fetch_snapshot(meta, depth_k=5, retries=3, prefer_liquid_token=True)
            # Respect rate limiting
            if SETTINGS.SNAPSHOT_SLEEP_S > 0:
                time.sleep(SETTINGS.SNAPSHOT_SLEEP_S)

            # Persist snapshot (even if ok_clob is False; useful for diagnostics)
            store.insert_snapshot(
                SnapshotRow(
                    ts=cycle_ts,
                    market_id=meta.market_id,
                    slug=meta.slug,
                    token_id=snap.token_id,
                    vol24h=float(snap.vol24h or 0.0),
                    liquidity=float(snap.liquidity or 0.0),
                    mid=snap.mid,
                    spread=snap.spread,
                    depth5=snap.depth5,
                    ok_clob=1 if snap.ok_clob else 0,
                    restricted=1 if meta.restricted else 0,
                )
            )

            # Screening: use A thresholds for BOT-ish, H thresholds for HUMAN-ish later.
            # For now, screen both; we'll route after score.
            resA = screener.screen(family="A", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)
            resH = screener.screen(family="H", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)

            if not (resA.ok or resH.ok):
                continue
            ok_count += 1

            # BotScore from snapshot delta
            lm = last_mid.get(meta.market_id)
            mid_move = 0.0 if (lm is None or snap.mid is None) else abs(snap.mid - lm)
            last_mid[meta.market_id] = snap.mid

            bs = botscore_v0(
                BotScoreInputs(
                    mid_move_abs=mid_move,
                    spread=snap.spread,
                    depth5=snap.depth5,
                    vol24h=float(snap.vol24h or 0.0),
                )
            )
            regime = regime_from_score(bs)
            store.insert_botscore(BotScoreRow(ts=cycle_ts, market_id=meta.market_id, token_id=snap.token_id, botscore=bs, regime=regime))

            # Update rolling medians for A2
            if snap.spread is not None:
                rolling[meta.market_id].spreads.append(float(snap.spread))
            if snap.depth5 is not None:
                rolling[meta.market_id].depths.append(float(snap.depth5))
            med_spread, med_depth = rolling[meta.market_id].medians()

            # Router
            if regime in ("BOT", "MIXED"):
                # Prefer A screening
                if not resA.ok:
                    continue
                st = a2_state.get(meta.market_id, A2State())
                sig = a2_detect(
                    curr_mid=snap.mid,
                    curr_spread=snap.spread,
                    curr_depth5=snap.depth5,
                    med_spread=med_spread,
                    med_depth5=med_depth,
                    state=st,
                    p=a2_params
                )
                a2_state[meta.market_id] = A2State(last_mid=snap.mid, last_spread=snap.spread, last_depth5=snap.depth5)

                if sig.fired:
                    a2_fires += 1
                    store.insert_signal(SignalRow(
                        ts=cycle_ts,
                        market_id=meta.market_id,
                        token_id=snap.token_id,
                        strategy="A2",
                        signal="FADE_CASCADE",
                        strength=float(sig.strength),
                        details=sig.details
                    ))

                    # Prepare an order intent (paper)
                    intent = OrderIntent(
                        token_id=snap.token_id,
                        side="SELL",   # placeholder: direction logic needs YES/NO semantics; keep as paper intent
                        price=float(snap.mid or 0.5),
                        size=screener.S() * 0.25,  # tactical sizing
                        reason="A2 cascade detected",
                        strategy="A2"
                    )
                    execution.place_order(intent)  # no-op in research
            else:
                # HUMAN regime → H1 candidate (manual checklist)
                if not resH.ok:
                    continue
                h1_candidates += 1
                store.insert_signal(SignalRow(
                    ts=cycle_ts,
                    market_id=meta.market_id,
                    token_id=snap.token_id,
                    strategy="H1",
                    signal="CANDIDATE",
                    strength=0.5,
                    details="Human-regime candidate; run wording/resolution checklist manually."
                ))

        print(f"Screenable markets: {ok_count} | A2 fires: {a2_fires} | H1 candidates: {h1_candidates}")
        time.sleep(SETTINGS.LOOP_SLEEP_S)


if __name__ == "__main__":
    main()
