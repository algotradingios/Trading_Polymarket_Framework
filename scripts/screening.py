from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.clients import MarketDataProvider
from src.domain.screening import ScreeningConfig, ScreeningEngine
from src.config.settings import SETTINGS


def get_user_input() -> str:
    """Get single character input from user (space for more, q to quit)."""
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch
    except (ImportError, OSError, AttributeError):
        # Fallback for non-Unix systems or when termios is not available
        try:
            user_input = input().strip()
            return user_input[0] if user_input else ' '
        except (EOFError, KeyboardInterrupt):
            return 'q'


def main() -> None:
    
    provider = MarketDataProvider(
        gamma_host=SETTINGS.GAMMA_HOST,
        clob_host=SETTINGS.CLOB_HOST,
        chain_id=SETTINGS.CHAIN_ID,
    )

    scfg = ScreeningConfig(
        equity=SETTINGS.EQUITY,
        target_pos_frac=SETTINGS.TARGET_POS_FRAC,
    )
    screener = ScreeningEngine(scfg)

    # 1) Fetch open markets
    metas = provider.list_open_markets_universe(
        pages=SETTINGS.PAGES,
        limit=SETTINGS.LIMIT,
        order=SETTINGS.ORDER,
        ascending=SETTINGS.ASCENDING,
        only_open=True,
        allow_restricted=SETTINGS.ALLOW_RESTRICTED,
        require_tokens=True,
    )

    print("\n" + "="*80)
    print("POLYMARKET MARKET SCREENING")
    print("="*80)
    print(f"\nTotal candidates (open & tokenized): {len(metas)}")
    print("\nStrategy Families:")
    print("  [A] = Microstructure-based Alpha (A*)")
    print("        - Requires HIGH liquidity (depth5 ≥ 8x position size, vol24h ≥ 20x)")
    print("        - Strategies: liquidity cascades, spread explosions, mechanical moves")
    print("  [H] = Information-based Alpha (H*)")
    print("        - Requires MODERATE liquidity (depth5 ≥ 3x position size, vol24h ≥ 10x)")
    print("        - Strategies: wording ambiguity, resolution mechanics, mispriced probabilities")
    print("\n" + "-"*80)
    print("Markets passing screening (showing 10 at a time):")
    print("-"*80 + "\n")

    # 2) Screen markets and collect results
    results: list[tuple[str, float, float, float, float, bool, bool]] = []  # slug, depth5, vol24h, exit_A, exit_H, ok_A, ok_H
    ok_A, ok_H = 0, 0

    for meta in metas[:200]:
        snap = provider.fetch_snapshot(meta, depth_k=5, retries=3, prefer_liquid_token=True)

        resA = screener.screen(family="A", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)
        resH = screener.screen(family="H", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)

        if resA.ok or resH.ok:
            results.append((
                snap.slug,
                snap.depth5 or 0.0,
                snap.vol24h or 0.0,
                resA.exit_risk or 0.0,
                resH.exit_risk or 0.0,
                resA.ok,
                resH.ok,
            ))
            if resA.ok:
                ok_A += 1
            if resH.ok:
                ok_H += 1

    # 3) Display results with pagination
    page_size = 10
    current_page = 0
    total_pages = (len(results) + page_size - 1) // page_size

    while current_page < total_pages:
        start_idx = current_page * page_size
        end_idx = min(start_idx + page_size, len(results))
        
        print(f"\nPage {current_page + 1}/{total_pages} (showing {start_idx + 1}-{end_idx} of {len(results)} markets)\n")
        
        for i in range(start_idx, end_idx):
            slug, depth5, vol24h, exit_A, exit_H, ok_A_market, ok_H_market = results[i]
            
            tags = []
            if ok_A_market:
                tags.append("A")
            if ok_H_market:
                tags.append("H")
            
            tag_str = f"[{'+'.join(tags)} OK]" if tags else "[FAIL]"
            
            # Show exit risk for the strategy family that passed (or both if both passed)
            exit_str = ""
            if ok_A_market and ok_H_market:
                exit_str = f"exit_A={exit_A:.3f} exit_H={exit_H:.3f}"
            elif ok_A_market:
                exit_str = f"exit_A={exit_A:.3f}"
            elif ok_H_market:
                exit_str = f"exit_H={exit_H:.3f}"
            
            print(f"{tag_str:8s} {slug:50s} depth5={depth5:>10.0f} vol24h={vol24h:>12.0f} {exit_str}")
        
        current_page += 1
        
        if current_page < total_pages:
            print(f"\n{'─'*80}")
            print("Press SPACE for more markets, or 'q' to quit: ", end="", flush=True)
            try:
                user_input = get_user_input()
                print()  # New line after input
                
                if user_input.lower() == 'q' or user_input == '\x03':  # Ctrl+C
                    break
            except (KeyboardInterrupt, EOFError):
                print("\n")
                break
        else:
            print(f"\n{'─'*80}")
            print("End of results.")

    print(f"\n{'='*80}")
    print(f"Summary: {ok_A} markets passed [A] screening, {ok_H} markets passed [H] screening")
    print(f"Total unique markets passing at least one screen: {len(results)}")
    print("="*80)


if __name__ == "__main__":
    main()
