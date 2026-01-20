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
