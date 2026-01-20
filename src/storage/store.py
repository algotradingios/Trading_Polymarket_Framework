from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class SnapshotRow:
    ts: int
    market_id: str
    slug: str
    token_id: str
    vol24h: float
    liquidity: float
    mid: Optional[float]
    spread: Optional[float]
    depth5: Optional[float]
    ok_clob: int
    restricted: int

@dataclass(frozen=True)
class BotScoreRow:
    ts: int
    market_id: str
    token_id: str
    botscore: float
    regime: str

@dataclass(frozen=True)
class SignalRow:
    ts: int
    market_id: str
    token_id: str
    strategy: str
    signal: str
    strength: float
    details: str

class Store:
    def __init__(self, path: str):
        self.path = path
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as con:
            cur = con.cursor()
            cur.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                ts INTEGER,
                market_id TEXT,
                slug TEXT,
                token_id TEXT,
                vol24h REAL,
                liquidity REAL,
                mid REAL,
                spread REAL,
                depth5 REAL,
                ok_clob INTEGER,
                restricted INTEGER
            )""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS bot_scores (
                ts INTEGER,
                market_id TEXT,
                token_id TEXT,
                botscore REAL,
                regime TEXT
            )""")
            cur.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                ts INTEGER,
                market_id TEXT,
                token_id TEXT,
                strategy TEXT,
                signal TEXT,
                strength REAL,
                details TEXT
            )""")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_snap_mkt_ts ON snapshots(market_id, ts)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bs_mkt_ts ON bot_scores(market_id, ts)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sig_mkt_ts ON signals(market_id, ts)")
            con.commit()

    def now_ts(self) -> int:
        return int(time.time())

    def insert_snapshot(self, r: SnapshotRow) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (r.ts, r.market_id, r.slug, r.token_id, r.vol24h, r.liquidity,
                 r.mid, r.spread, r.depth5, r.ok_clob, r.restricted)
            )
            con.commit()

    def insert_botscore(self, r: BotScoreRow) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO bot_scores VALUES (?,?,?,?,?)",
                (r.ts, r.market_id, r.token_id, r.botscore, r.regime)
            )
            con.commit()

    def insert_signal(self, r: SignalRow) -> None:
        with sqlite3.connect(self.path) as con:
            con.execute(
                "INSERT INTO signals VALUES (?,?,?,?,?,?,?)",
                (r.ts, r.market_id, r.token_id, r.strategy, r.signal, r.strength, r.details)
            )
            con.commit()
