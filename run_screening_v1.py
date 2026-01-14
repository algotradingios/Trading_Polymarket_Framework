from __future__ import annotations

from providers import MarketDataProvider
import providers
print("providers loaded from:", providers.__file__)

from screening_engine import ScreeningConfig, ScreeningEngine


def main() -> None:
    provider = MarketDataProvider(
        gamma_host="https://gamma-api.polymarket.com",
        clob_host="https://clob.polymarket.com",
        chain_id=137,
    )

    # Ajusta esto a tu capital real asignado
    scfg = ScreeningConfig(equity=10_000.0, target_pos_frac=0.01)
    screener = ScreeningEngine(scfg)

    # 1) Traer candidatos "abiertos" (importantísimo para evitar tu problema de mercados históricos)
    metas = provider.list_open_unrestricted_markets(
        pages=15,
        limit=100,
        order="volume24hr",
        ascending=False,
        require_orderbook=False,
        hydrate_missing_tokens=True,
    )


    print("First 5 candidates:")
    for mm in metas[:5]:
        print(" -", mm.slug, "closed=", mm.closed, "vol24h=", mm.volume24h, "tokens=", len(mm.clob_token_ids))


    print(f"Candidates(open & tokenized): {len(metas)}")

    # 2) Snapshot y screening (en V0.1 aún no sabemos el régimen; probamos A y H)
    ok_A, ok_H = 0, 0

    for meta in metas[:200]:
        snap = provider.fetch_snapshot(meta, depth_k=5, retries=3, prefer_liquid_token=True)

        resA = screener.screen(family="A", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)
        resH = screener.screen(family="H", vol24h=snap.vol24h, depth5=snap.depth5, ok_clob=snap.ok_clob)

        if resA.ok:
            ok_A += 1
            print(f"[A OK] {snap.slug:50s} depth5={snap.depth5:.0f} vol24h={snap.vol24h:.0f} exit={resA.exit_risk:.3f}")
        if resH.ok:
            ok_H += 1
            print(f"[H OK] {snap.slug:50s} depth5={snap.depth5:.0f} vol24h={snap.vol24h:.0f} exit={resH.exit_risk:.3f}")

    print(f"\nScreening OK counts: A={ok_A}, H={ok_H}")


if __name__ == "__main__":
    main()
