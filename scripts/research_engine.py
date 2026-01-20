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
        skipped_no_clob = 0
        skipped_screening = 0
        skipped_regime = 0
        
        # Track markets for detailed output
        market_details: list[tuple[str, str, float, str, bool, bool, str]] = []  # slug, regime, botscore, resA, resH, routing

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
            
            if not snap.ok_clob:
                skipped_no_clob += 1
                continue

            # Screening: use A thresholds for BOT-ish, H thresholds for HUMAN-ish later.
            # For now, screen both; we'll route after score.
            resA = screener.screen(family="A", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)
            resH = screener.screen(family="H", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)

            if not (resA.ok or resH.ok):
                skipped_screening += 1
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
            routing = ""
            if regime in ("BOT", "MIXED"):
                # Prefer A screening
                if not resA.ok:
                    skipped_regime += 1
                    routing = f"BOT/MIXED but A screening failed (depth5={snap.depth5:.0f} need≥{resA.depth5_min:.0f}, vol24h={snap.vol24h:.0f} need≥{resA.vol24h_min:.0f})"
                    market_details.append((meta.slug, regime, bs, resA.ok, resH.ok, routing))
                    continue
                routing = f"→ A2 (BOT/MIXED regime)"
                st = a2_state.get(meta.market_id, A2State())
                
                # Show A2 detection details
                spread_str = f"{med_spread:.6f}" if med_spread is not None else "None"
                depth_str = f"{med_depth:.0f}" if med_depth is not None else "None"
                hist_status = f"hist: spread={spread_str}, depth={depth_str}"
                
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
                    routing += f" [FIRED: {sig.details}]"
                    store.insert_signal(SignalRow(
                        ts=cycle_ts,
                        market_id=meta.market_id,
                        token_id=snap.token_id,
                        strategy="A2",
                        signal="FADE_CASCADE",
                        strength=float(sig.strength),
                        details=sig.details
                    ))
                    print(f"  [DB] ✅ Signal inserted: A2 FADE_CASCADE for {meta.slug[:50]} (strength={sig.strength:.3f}, {sig.details})")

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
                    routing += f" [no signal: {sig.details}] ({hist_status})"
            else:
                # HUMAN regime → H1 candidate (manual checklist)
                if not resH.ok:
                    skipped_regime += 1
                    routing = f"HUMAN but H screening failed"
                    market_details.append((meta.slug, regime, bs, resA.ok, resH.ok, routing))
                    continue
                routing = f"→ H1 (HUMAN regime)"
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
                print(f"  [DB] Signal inserted: H1 CANDIDATE for {meta.slug[:50]}")
            
            market_details.append((meta.slug, regime, bs, resA.ok, resH.ok, routing))
            # Show detailed info for markets that pass screening
            print(f"  [DB] Snapshot: {meta.slug[:50]:50s}")
            print(f"       BotScore={bs:.3f} ({regime:6s}) | A={resA.ok} H={resH.ok} | depth5={snap.depth5:.0f} vol24h={snap.vol24h:.0f}")
            print(f"       {routing}")

        # Summary output
        print(f"\n{'='*100}")
        print(f"Cycle Summary:")
        print(f"  Screenable markets: {ok_count}")
        print(f"  A2 fires: {a2_fires}")
        print(f"  H1 candidates: {h1_candidates}")
        print(f"\n  Filtered out:")
        print(f"    No CLOB access: {skipped_no_clob}")
        print(f"    Failed screening (A & H): {skipped_screening}")
        print(f"    Regime mismatch: {skipped_regime}")
        
        # Show markets grouped by regime
        if market_details:
            bot_markets = [m for m in market_details if m[1] in ("BOT", "MIXED")]
            human_markets = [m for m in market_details if m[1] == "HUMAN"]
            
            print(f"\n  Markets by Regime (for strategy routing):")
            print(f"    BOT/MIXED markets ({len(bot_markets)}): → A2 strategy (microstructure-based)")
            for slug, regime, bs, okA, okH, routing in sorted(bot_markets, key=lambda x: x[2], reverse=True)[:5]:
                tags = []
                if okA:
                    tags.append("A")
                if okH:
                    tags.append("H")
                tag_str = f"[{'+'.join(tags)}]" if tags else "[--]"
                print(f"      {tag_str:6s} {slug[:45]:45s} BotScore={bs:.3f} ({regime:6s})")
            
            print(f"\n    HUMAN markets ({len(human_markets)}): → H1 strategy (information-based)")
            for slug, regime, bs, okA, okH, routing in sorted(human_markets, key=lambda x: x[2], reverse=False)[:5]:
                tags = []
                if okA:
                    tags.append("A")
                if okH:
                    tags.append("H")
                tag_str = f"[{'+'.join(tags)}]" if tags else "[--]"
                print(f"      {tag_str:6s} {slug[:45]:45s} BotScore={bs:.3f} ({regime:6s})")
            
            if len(bot_markets) > 5 or len(human_markets) > 5:
                print(f"    ... (showing top 5 of each regime)")
            
            # Explain why A2/H1 aren't firing
            if a2_fires == 0 and len(bot_markets) > 0:
                print(f"\n  ⚠️  A2 not firing: Requires cascade conditions (spread expansion + depth collapse + mid jump)")
                print(f"     Need at least 2/3 conditions. Historical medians are being built up over cycles.")
            if h1_candidates == 0 and len(human_markets) == 0:
                print(f"\n  ⚠️  H1 candidates: 0 (all markets classified as BOT/MIXED)")
                print(f"     BotScore calculation may need tuning. Current threshold: BOT≥0.65, HUMAN≤0.40")
        
        print(f"{'='*100}")
        time.sleep(SETTINGS.LOOP_SLEEP_S)


if __name__ == "__main__":
    main()
