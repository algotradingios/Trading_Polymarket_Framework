# Polymarket Quantitative Research Framework

A modular, capital-aware, Python-based framework for **quantitative research on Polymarket prediction markets**, with a strict separation between **research** and **execution**.

This repository is designed to let you:

- Analyze live Polymarket markets from any location
- Study liquidity, microstructure, and behavioral inefficiencies
- Design and validate strategies in paper/research mode
- Deploy the same logic to execution **only** in jurisdictions where trading is permitted

---

## ⚠️ Important Notice (Read First)

From **Spain, the EU, and many other jurisdictions**, Polymarket markets are returned as:

```text
restricted = true
```

This means:

- You can read market data (Gamma API, CLOB order books)
- You cannot place trades from that environment
- This is regulatory / jurisdictional, not a bug

**This framework does not bypass restrictions.**

Instead, it is explicitly designed to:

- Work fully in research mode everywhere
- Be deployable for execution unchanged in a permitted environment

### What This Repository Is

- A research-grade quantitative framework for prediction markets
- A tool for alpha discovery, not blind automation
- A system that treats liquidity, exit risk, and regime changes as first-class constraints
- A foundation you can later deploy for execution without refactoring

### What This Repository Is NOT

- A trading bot you can run blindly
- A way to bypass geographic or legal restrictions
- Financial or legal advice
- A guarantee of profitability

## Core Capabilities

### 1. Market Universe Discovery

- Pulls live markets from the Polymarket Gamma API
- Orders markets by activity (e.g. `volume24hr`)
- Handles multiple API payload variants robustly
- Works even when `restricted=true`

### 2. Liquidity & Exit Feasibility Screening

Markets are filtered using capital-aware constraints:

- Minimum 24h volume
- Top-of-book depth (Depth5 proxy)
- Exit risk (position size vs volume)
- Strategy-specific thresholds

This prevents "fake alpha" that only works at infinitesimal size.

### 3. Market Regime Classification (BotScore V0)

Markets are classified as:

- **BOT-dominated**
- **HUMAN-dominated**
- **MIXED**

Using observable microstructure proxies:

- Quote churn
- Price movement per unit volume
- Order book symmetry
- Book update vs trade ratio

### 4. Strategy Families

- **A\*** — Automated / microstructure strategies
  - Liquidity cascades
  - Spread explosions
  - Mechanical dislocations

- **H\*** — Human / informational strategies
  - Wording ambiguity
  - Resolution mechanics
  - Scenario mispricing

Each strategy is only considered valid in its appropriate regime.

### 5. Research Mode (Default)

- Fully functional from any location (Spain/EU/UK/US)
- Reads live market data
- Generates signals
- Logs paper PnL
- Places no trades

### 6. Execution Mode (Optional, Disabled)

- Uses the exact same logic as research mode
- Requires a permitted runtime environment
- Execution is isolated behind an adapter and disabled by default

## Installation

This repository uses `uv` for dependency management.

### Prerequisites

- Python 3.10+
- `uv`

### Setup

```bash
uv sync
```

This creates a reproducible environment based on `pyproject.toml` and `uv.lock`.

## Quickstart (Research Mode)

### 1) Check your environment's restriction status

This is the recommended first step.

```bash
uv run python -m scripts.diagnostics
```

This script prints:

- How many markets are restricted
- How many are open (`closed=false`)
- Whether outcome tokens (`clobTokenIds`) are present

From Spain/EU, you should expect all major markets to be restricted.

### 2) Build a market universe and screen it

```bash
uv run python -m scripts.screening
```

This will:

- Discover open markets
- Apply liquidity and exit-risk screening
- Report how many markets are usable for research

You will typically see:

- Many candidates in research mode
- Zero candidates in execution mode (expected in restricted jurisdictions)

### 3) Run the research engine

```bash
uv run python -m scripts.research_engine
```

This runs the main research loop that:
- Continuously monitors markets
- Applies screening and bot score classification
- Detects A2 cascade signals
- Stores results in SQLite database

### 4) Adjust capital assumptions

Screening is capital-aware. Edit your configuration in `src/config/settings.py`:

```python
EQUITY: float = 10_000.0
TARGET_POS_FRAC: float = 0.01  # 1% per position
```

Smaller capital assumptions allow more markets to pass exit-risk constraints.

## Command Output Examples

This section provides example outputs for each command and explains what they mean.

### 1. Diagnostics (`scripts.diagnostics`)

**Command:**
```bash
uv run python -m scripts.diagnostics
```

**Example Output:**
```
=== A) /markets ordered by volume24hr (no filters) ===
count: 50
active: {True: 50}
closed: {False: 20, True: 30}
archived: {False: 50}
restricted: {True: 50}
has clobTokenIds: 50

=== B) /markets closed=false ===
count: 50
active: {True: 50}
closed: {False: 50}
archived: {False: 50}
restricted: {True: 50}
has clobTokenIds: 50

=== C) /markets closed=false & restricted=false ===
count: 0
```

**What This Means:**
- **Section A**: Shows all markets returned by Gamma API, ordered by 24h volume. In restricted jurisdictions (like Spain/EU), all markets show `restricted: {True: 50}`, meaning you can read data but cannot trade.
- **Section B**: Filters for open markets (`closed=false`). All 50 markets are open and have token IDs (`clobTokenIds`), meaning they're tradeable (if not restricted).
- **Section C**: Shows markets that are both open AND unrestricted. In restricted jurisdictions, this will be `0`, confirming you cannot trade from your location.

**Key Takeaway**: This confirms your environment's restriction status. If Section C shows 0 markets, you're in a restricted jurisdiction and should use research mode only.

### 2. Screening (`scripts.screening`)

**Command:**
```bash
uv run python -m scripts.screening
```

**Example Output:**
```
================================================================================
POLYMARKET MARKET SCREENING
================================================================================

Total candidates (open & tokenized): 995

Strategy Families:
  [A] = Microstructure-based Alpha (A*)
        - Requires HIGH liquidity (depth5 ≥ 8x position size, vol24h ≥ 20x)
        - Strategies: liquidity cascades, spread explosions, mechanical moves
  [H] = Information-based Alpha (H*)
        - Requires MODERATE liquidity (depth5 ≥ 3x position size, vol24h ≥ 10x)
        - Strategies: wording ambiguity, resolution mechanics, mispriced probabilities

--------------------------------------------------------------------------------
Markets passing screening (showing 10 at a time):
--------------------------------------------------------------------------------

Page 1/20 (showing 1-10 of 200 markets)

[A+H OK] will-melania-say-career-during-ai-talk-on-friday   depth5=    185311 vol24h=    15069913 exit_A=0.000 exit_H=0.000
[A+H OK] fed-decreases-interest-rates-by-50-bps-after-january-2026-meeting depth5=  13027998 vol24h=     5394628 exit_A=0.000 exit_H=0.000
[A OK] will-trump-acquire-greenland-before-2027           depth5=   1217740 vol24h=     1826790 exit_A=0.000 exit_H=0.001
[H OK] bitcoin-above-100k-on-january-20                  depth5=    44811 vol24h=     646879 exit_A=0.002 exit_H=0.001

Press SPACE for more markets, or 'q' to quit:
```

**What This Means:**
- **Total candidates**: 995 markets are open and have token IDs available.
- **Strategy Tags**:
  - `[A+H OK]`: Market passes both A* (microstructure) and H* (information) screening thresholds
  - `[A OK]`: Market passes only A* screening (high liquidity required)
  - `[H OK]`: Market passes only H* screening (moderate liquidity sufficient)
- **depth5**: Sum of top 5 levels of order book liquidity (notional value). Higher = more liquid.
- **vol24h**: 24-hour trading volume. Higher = more active market.
- **exit_A / exit_H**: Exit risk = position size / volume24h. Lower is better (0.000 = very safe, 0.001 = 0.1% of daily volume, 0.002 = 0.2% of daily volume).
- **Pagination**: Shows 10 markets at a time. Press SPACE for more, 'q' to quit.

**Key Takeaway**: Markets with `[A+H OK]` can be used for both strategy families. Markets with only `[A OK]` or `[H OK]` are suitable for one family only.

### 3. Research Engine (`scripts.research_engine`)

**Command:**
```bash
uv run python -m scripts.research_engine
```

**Example Output:**
```
=== Research Engine starting ===
ALLOW_RESTRICTED = True
EXECUTION_ENABLED = False
DB = research.db

[2026-01-20 11:15:30] Universe size: 80
  [DB] Snapshot: will-melania-say-career-during-ai-talk-on-friday  
       BotScore=0.429 (MIXED ) | A=True H=True | depth5=185311 vol24h=15069913
       → A2 (BOT/MIXED regime) [no signal: NO_CASCADE] (hist: spread=0.001000, depth=185311)
  [DB] Snapshot: fed-decreases-interest-rates-by-50-bps-after-january-2026-meeting
       BotScore=0.555 (MIXED ) | A=True H=True | depth5=13027996 vol24h=5394628
       → A2 (BOT/MIXED regime) [no signal: NO_CASCADE] (hist: spread=0.001000, depth=13027996)
  [DB] Snapshot: will-trump-acquire-greenland-before-2027          
       BotScore=0.258 (HUMAN ) | A=True H=True | depth5=1217740 vol24h=1826790
       → H1 (HUMAN regime)
  [DB] ✅ Signal inserted: H1 CANDIDATE for will-trump-acquire-greenland-before-2027
  [DB] Snapshot: bitcoin-above-100k-on-january-20                  
       BotScore=0.227 (HUMAN ) | A=True H=True | depth5=44811 vol24h=646879
       → H1 (HUMAN regime)
  [DB] ✅ Signal inserted: H1 CANDIDATE for bitcoin-above-100k-on-january-20

====================================================================================================
Cycle Summary:
  Screenable markets: 80
  A2 fires: 0
  H1 candidates: 12

  Filtered out:
    No CLOB access: 15
    Failed screening (A & H): 5
    Regime mismatch: 0

  Markets by Regime (for strategy routing):
    BOT/MIXED markets (68): → A2 strategy (microstructure-based)
      [A+H] will-melania-say-career-during-ai-talk-on-friday   BotScore=0.429 (MIXED )
      [A+H] fed-decreases-interest-rates-by-50-bps-after-january-2026-meeting BotScore=0.555 (MIXED )
      [A+H] will-the-memphis-grizzlies-win-the-2026-nba-finals BotScore=0.554 (MIXED )
      [A+H] fed-increases-interest-rates-by-25-bps-after-january-2026-meeting BotScore=0.611 (MIXED )
      [A+H] will-slavia-pragu-win-the-202526-champions-league BotScore=0.677 (BOT   )

    HUMAN markets (12): → H1 strategy (information-based)
      [A+H] will-trump-acquire-greenland-before-2027           BotScore=0.258 (HUMAN )
      [A+H] bitcoin-above-100k-on-january-20                  BotScore=0.227 (HUMAN )
      [A+H] will-andr-ventura-win-the-2026-portugal-presidential-election BotScore=0.354 (HUMAN )

  ⚠️  A2 not firing: Requires cascade conditions (spread expansion + depth collapse + mid jump)
     Need at least 2/3 conditions. Historical medians are being built up over cycles.
====================================================================================================
```

**What This Means:**
- **Universe size**: Number of markets being monitored in this cycle (80 markets).
- **`[DB] Snapshot`**: Each market's data is written to the SQLite database (`research.db`).
- **BotScore**: Market regime classification score (0.0-1.0). See detailed explanation below.
- **Regime Classification**:
  - `BOT` (BotScore ≥ 0.65): Bot-dominated markets, suitable for A2 microstructure strategies
  - `MIXED` (0.40 < BotScore < 0.65): Mixed regime, can use A2 strategies
  - `HUMAN` (BotScore ≤ 0.40): Human-dominated markets, suitable for H1 information strategies
- **Routing**:
  - `→ A2 (BOT/MIXED regime)`: Market routed to A2 cascade detector
  - `→ H1 (HUMAN regime)`: Market routed to H1 information strategy
- **Signal Status**:
  - `[no signal: NO_CASCADE]`: A2 detector checked but no cascade conditions met
  - `✅ Signal inserted: H1 CANDIDATE`: H1 candidate found and stored in database
- **Cycle Summary**:
  - **Screenable markets**: Markets that passed liquidity screening (80)
  - **A2 fires**: Number of A2 cascade signals detected (0 = no cascades found)
  - **H1 candidates**: Number of HUMAN regime markets suitable for H1 (12)
  - **Filtered out**: Markets excluded due to no CLOB access, failed screening, or regime mismatch
- **Historical medians**: A2 detector needs ~30 cycles to build rolling medians for cascade detection.

**Key Takeaway**: The research engine continuously monitors markets, classifies them by regime, and routes them to appropriate strategies. Signals are stored in the database for analysis.

### 4. Data Audit (`scripts.data_audit`)

**Command:**
```bash
uv run python -m scripts.data_audit --pages 2 --limit 50
```

**Example Output:**
```
=== DATA AUDIT SUMMARY ===
Gamma host: https://gamma-api.polymarket.com
CLOB  host: https://clob.polymarket.com (chain_id=137)
Markets fetched: 100
Markets with token ids: 100 (100.0%)

--- Gamma field availability (top 30 keys) ---
id                                 100  (100.0%)
question                           100  (100.0%)
volume24hr                         100  (100.0%)
clobTokenIds                       100  (100.0%)
...

--- Vol24h availability ---
Markets with any Vol24h key parsed: 100/100 (100.0%)
Vol key usage breakdown:
  volume24hr               83
  volume                   17

--- Market status ---
Open markets (closed=False, archived=False): 100/100

--- CLOB access quality (for open markets with token_ids) ---
Markets tested: 100
Order book success: 100/100 (100.0%)
Midpoint   success: 100/100 (100.0%)
Spread     success: 100/100 (100.0%)

--- Basic distributions (proxies) ---
Depth5 notional proxy: n=100 p10=3515.68 p50=12844.9 p90=1.13897e+06 max=1.09848e+07
Spread: n=100 p10=0.001 p50=0.002 p90=0.0221 max=0.25
Midpoint: n=100 p10=0.0005 p50=0.0065 p90=0.5678 max=0.9935
```

**What This Means:**
- **Gamma field availability**: Shows which fields are present in Gamma API responses. 100% means all markets have this field.
- **Vol24h availability**: Confirms volume data is available. `volume24hr` is the primary key (83 markets), `volume` is fallback (17 markets).
- **CLOB access quality**: Tests order book, midpoint, and spread API calls. 100% success means all markets have accessible order books.
- **Basic distributions**: Statistical summary of market microstructure:
  - **Depth5**: p10=3,515 (10th percentile), p50=12,844 (median), p90=1.14M (90th percentile)
  - **Spread**: p10=0.001 (very tight), p50=0.002 (tight), p90=0.022 (moderate)
  - **Midpoint**: Price levels range from 0.0005 to 0.9935

**Key Takeaway**: This audit confirms data quality and API reliability. Use this to verify your environment can access market data correctly.

## BotScore Calculation Explained

The BotScore is a composite metric (0.0 to 1.0) that classifies markets into three regimes:

- **BOT** (≥ 0.65): Bot-dominated markets with high-frequency trading, tight spreads, and mechanical price movements
- **HUMAN** (≤ 0.40): Human-dominated markets with information-driven trading, wider spreads, and narrative-driven moves
- **MIXED** (0.40-0.65): Markets with characteristics of both regimes

### Calculation Formula

BotScore is calculated as a weighted combination of four components:

```
BotScore = 0.30 × PMWV_score + 0.25 × Spread_score + 0.25 × Depth_score + 0.20 × Stability_score
```

### Component 1: PMWV Score (30% weight)

**PMWV** = Price Movement per Unit Volume = `|Δmid| / volume24h`

- **Higher PMWV** = More bot-like (bots create noise/volatility without proportional volume)
- **Lower PMWV** = More human-like (price moves reflect information, not noise)

**Scoring:**
```
pmwv = mid_move_abs / max(vol24h, 1e-9)
pmwv_score = log(1 + pmwv × 10000) / log(10001)
```

Uses logarithmic scaling to handle wide ranges (typical PMWV: 0.000001 to 0.1).

### Component 2: Spread Tightness Score (25% weight)

**Spread** = Bid-Ask spread (absolute value, not percentage)

- **Tighter spreads** (< 0.002) = More bot-like (active market making)
- **Wider spreads** (> 0.05) = More human-like (less continuous market making)

**Scoring:**
```
spread_score = 1.0 / (1.0 + spread × 100)
```

Uses inverse sigmoid: tight spreads (0.001) → score ≈ 0.91, wide spreads (0.1) → score ≈ 0.09.

### Component 3: Depth-to-Volume Ratio Score (25% weight)

**Depth/Volume Ratio** = `depth5 / volume24h`

- **Higher ratio** = More bot-like (liquidity provision relative to trading activity)
- **Lower ratio** = More human-like (less liquidity provision)

**Scoring:**
```
depth_vol_ratio = depth5 / max(vol24h, 1e-9)
depth_score = log(1 + ratio) / log(11)
```

Uses logarithmic scaling (typical range: 0.01 to 10+).

### Component 4: Spread Stability Score (20% weight)

**Stability Proxy** = Current spread level as indicator of market making activity

- **Very tight spreads** (< 0.002) = Active market making (bot-like)
- **Moderate spreads** (0.01-0.05) = Mixed regime
- **Wide spreads** (> 0.05) = Less market making (human-like)

**Scoring:**
```
if spread < 0.002:    stability_score = 1.0   # Very tight = bot-like
elif spread < 0.01:   stability_score = 0.7   # Tight = somewhat bot-like
elif spread < 0.05:   stability_score = 0.4   # Moderate = mixed
else:                 stability_score = 0.2   # Wide = human-like
```

### Example Calculation

For a market with:
- `mid_move_abs = 0.01` (price moved 0.01)
- `vol24h = 1,000,000` (1M volume)
- `spread = 0.001` (very tight)
- `depth5 = 500,000` (500K liquidity)

**Step 1: PMWV Score**
```
pmwv = 0.01 / 1,000,000 = 0.00001
pmwv_score = log(1 + 0.00001 × 10000) / log(10001) = log(1.1) / log(10001) ≈ 0.004
```

**Step 2: Spread Score**
```
spread_score = 1.0 / (1.0 + 0.001 × 100) = 1.0 / 1.1 ≈ 0.909
```

**Step 3: Depth Score**
```
depth_vol_ratio = 500,000 / 1,000,000 = 0.5
depth_score = log(1 + 0.5) / log(11) = log(1.5) / log(11) ≈ 0.115
```

**Step 4: Stability Score**
```
spread = 0.001 < 0.002 → stability_score = 1.0
```

**Final BotScore:**
```
BotScore = 0.30 × 0.004 + 0.25 × 0.909 + 0.25 × 0.115 + 0.20 × 1.0
         = 0.0012 + 0.227 + 0.029 + 0.20
         = 0.457 (MIXED regime)
```

### Interpretation

- **BotScore = 0.677** → **BOT regime**: High-frequency trading, tight spreads, high liquidity provision
- **BotScore = 0.429** → **MIXED regime**: Combination of bot and human characteristics
- **BotScore = 0.258** → **HUMAN regime**: Information-driven trading, wider spreads, lower liquidity provision

**Strategy Routing:**
- BOT/MIXED markets → A2 cascade detector (microstructure strategies)
- HUMAN markets → H1 information strategies (wording/resolution analysis)

## Research vs Execution Modes

### Research Mode (Default)

```python
ALLOW_RESTRICTED = True
EXECUTION_ENABLED = False
```

- Works everywhere
- No wallet required
- No orders placed
- Intended for strategy development and validation

### Execution Mode (Optional)

```python
ALLOW_RESTRICTED = False
EXECUTION_ENABLED = True
```

**Requires:**

- A jurisdiction where Polymarket allows trading
- A compliant runtime environment
- A wallet and signer
- Explicit user opt-in

## Recommended Deployment Architecture

```
Research Engine (anywhere)
        │
        ▼
Signals / Logs (JSON, DB)
        │
        ▼
Execution Engine (permitted jurisdiction)
        │
        ▼
Polymarket CLOB
```

This separation ensures:

- **Legal clarity**
- **Auditability**
- **Operational robustness**

## Repository Structure

```
polymarket_framework/
├── src/
│   ├── config/
│   │   └── settings.py          # Centralized configuration
│   ├── data/
│   │   ├── models.py            # Domain models (MarketMeta, MarketSnapshot)
│   │   └── clients.py           # Unified data access (Gamma & CLOB)
│   ├── domain/
│   │   ├── screening.py         # Liquidity & exit-risk screening
│   │   ├── microstructure.py   # Microstructure utilities
│   │   └── bot_score.py         # Market regime classification
│   ├── strategies/
│   │   ├── a2_cascade.py        # Microstructure cascade detection
│   │   └── h1_informational.py  # Informational strategy framework
│   ├── storage/
│   │   └── store.py             # SQLite storage
│   └── execution/
│       └── adapter.py           # Execution adapter
├── scripts/
│   ├── research_engine.py       # Main research loop
│   ├── screening.py             # Screening script
│   └── diagnostics.py           # Environment & API diagnostics
├── docs/
│   ├── README.md
│   ├── RESEARCH_METHODOLOGY.md
│   └── DEPLOYMENT_GUIDE.md
├── tests/                       # Test directory (ready for tests)
├── pyproject.toml
├── uv.lock
└── LICENSE
```

## Common Pitfalls

### "Candidates(open & tokenized): 0"

This usually means:

- You are filtering `restricted=false` in a restricted jurisdiction
- Or you are unintentionally excluding all markets

**Solution:** Run `python -m scripts.diagnostics` to confirm what Gamma returns in your environment.

### "Order book fetch fails"

- Some tokens have unstable books
- Rate limiting may apply

**Mitigations:**

- Retries and backoff (already supported)
- Small sleeps between calls
- Future upgrade to websockets

## License

MIT License. See [LICENSE](LICENSE) file.

## Final Notes

This project is intentionally:

- **Conservative**
- **Explicit about limitations**
- **Designed for serious quantitative research**

If you want to extend it further, natural next additions include:

- A paper-trading backtester aligned with live signals
- Statistical validation tooling
- A production execution checklist
- Monitoring and alerting

The framework is ready when you are ready to deploy it.

## Development Notes

Parts of this project were developed with the assistance of AI-based tools.
All architectural decisions, validation, and final responsibility remain with the author.
