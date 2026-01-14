# Polymarket Quantitative Research Framework

## Overview

This project is a modular, parametrized quantitative research framework for analyzing and designing trading strategies on Polymarket prediction markets, with a strong focus on:

- **Market screening and liquidity feasibility**
- **Detection of automated (bot-dominated) vs human-driven markets**
- **Microstructure-based alpha** (e.g. liquidity cascades, mechanical price moves)
- **Information-based alpha** (wording, resolution mechanics)
- **Clean separation between research and execution**

The framework is written in Python and is designed to be directly operable in research mode from any location, while keeping execution logic explicitly isolated due to regulatory and geographic constraints.

## Key Design Principles

### Research-first architecture
All alpha generation logic (screening, signals, regime detection) is fully functional without placing trades.

### Execution decoupling
Order placement is intentionally abstracted and disabled by default.

### Empirical robustness
All decisions (market inclusion, strategy eligibility) are driven by measurable quantities:

- Volume
- Order book depth
- Exit risk
- Market microstructure behavior

### Geographic awareness
The framework explicitly models and respects Polymarket's jurisdictional restrictions.

## Core Functionalities

### 1. Market Universe Construction

- Fetches markets from Polymarket Gamma API
- Orders markets by activity (e.g. volume24hr)
- Builds a universe of open markets
- Supports two modes:
  - **Research mode**: includes restricted markets
  - **Execution mode**: excludes restricted markets

**Key fields handled:**
- `active`, `closed`, `archived`, `restricted`
- `clobTokenIds`
- Liquidity and volume metrics

### 2. Liquidity & Exit Feasibility Screening

Each market is screened using capital-aware constraints:

- Minimum effective depth (Depth5 proxy)
- Minimum 24h volume
- Exit risk (position size relative to volume)
- Strategy-specific thresholds (A* vs H*)

This ensures the framework never proposes trades that are not realistically exitable.

### 3. Market Regime Classification (BotScore V0)

Markets are classified into regimes based on observable proxies:

- Quote churn
- Price movement per unit volume
- Order book symmetry
- Book update vs trade ratio

**Regimes:**
- **BOT-dominated**
- **HUMAN-dominated**
- **MIXED**

This classification routes markets to appropriate strategy families.

### 4. Strategy Families

#### A* — Automated / Microstructure Strategies

Designed for bot-dominated markets:

- Liquidity cascades
- Spread explosions
- Depth collapses
- Mechanical price jumps with low volume

**Includes:**
- Formal cascade detector (A2)
- Clear entry, exit, and stop logic
- Short holding times

#### H* — Human / Informational Strategies

Designed for human-driven markets:

- Ambiguous wording
- Resolution mechanics
- Mispriced probabilities

**Includes:**
- Formal checklist-based decision process
- Scenario trees
- Explicit thesis invalidation rules

### 5. Research Mode (Default)

In research mode, the framework:

- Analyzes all open markets, including `restricted=true`
- Computes signals and strategy eligibility
- Logs signals and simulated PnL
- Does not place trades

This mode is fully functional from jurisdictions such as:

- Spain
- EU
- UK
- US

### 6. Execution Mode (Optional, Disabled by Default)

Execution logic is intentionally isolated behind an adapter interface.

**Execution mode requires:**
- A runtime environment where Polymarket markets are not restricted
- A compliant wallet and signer
- Explicit user activation

**No execution code is enabled by default.**

## Geographic & Regulatory Limitations

### Important Notice

Polymarket applies jurisdiction-based access restrictions.

From certain locations (including Spain and most of the EU):

- Markets appear as `restricted=true`
- Order placement is blocked
- Only read-only access (market data) is permitted

**This framework does not bypass these restrictions.**

### Supported Modes by Geography

| Location | Research Mode | Execution Mode |
|----------|--------------|----------------|
| Spain / EU | ✅ Yes | ❌ No |
| UK | ✅ Yes | ❌ No |
| US | ⚠️ Limited | ❌ No |
| Allowed Jurisdictions | ✅ Yes | ✅ Yes |

> **Note:** Execution is only possible if the runtime environment is legally and technically permitted by Polymarket.

## Project Structure

```
.
├── providers.py          # Gamma & CLOB data access
├── screening_engine.py   # Liquidity & exit feasibility
├── bot_score.py          # Market regime classification
├── a2_detector.py        # Liquidity cascade detection
├── h1_checklist.py       # Informational strategy framework
├── run_screening_v1.py   # Research pipeline entry point
├── gamma_sanity.py       # API diagnostics
├── README.md
└── LICENSE
```

## Intended Use Cases

- Quantitative research on prediction markets
- Market microstructure analysis
- Strategy prototyping and validation
- Paper trading / simulated execution
- Preparation for deployment in permitted environments

## Non-Goals

- Circumventing geographic restrictions
- Providing legal advice
- Automating trading in restricted jurisdictions
- Offering financial recommendations
