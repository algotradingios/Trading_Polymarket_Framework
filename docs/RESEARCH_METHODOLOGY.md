# Research Methodology

## Purpose

This document describes the research methodology used in the Polymarket Quantitative Research Framework. Its goal is to ensure that all strategy development is:

- **Empirically grounded**
- **Reproducible**
- **Capital-aware**
- **Robust to market regime changes**
- **Clearly separated from execution constraints**

The methodology is designed for prediction markets, which differ materially from traditional financial markets.

## 1. Research Philosophy

### 1.1 Prediction Markets Are Not Efficient by Default

Unlike equities or futures:

- Participants are heterogeneous (retail, bots, ideologues, insiders)
- Liquidity is episodic
- Resolution mechanics introduce discrete payoff jumps
- Many participants are non-profit-maximizing

Therefore, the framework does not assume market efficiency and instead focuses on mechanistic and behavioral edges.

### 1.2 Edge Must Be Observable, Not Assumed

Every strategy must satisfy:

> **If the edge cannot be observed in live data, it is not an edge.**

This excludes:

- Purely narrative strategies without measurable mispricing
- Strategies relying on unverifiable information
- Post-hoc curve fitting

## 2. Research Pipeline Overview

The research pipeline follows a strict sequence:

1. **Universe Construction**
2. **Liquidity & Exit Screening**
3. **Market Regime Classification**
4. **Strategy Eligibility Filtering**
5. **Signal Generation**
6. **Paper PnL Attribution**
7. **Statistical Validation**

> **No step may be skipped.**

## 3. Universe Construction

### 3.1 Inclusion Criteria

A market enters the research universe if:

- `active == true`
- `closed == false`
- `archived == false`
- Outcome tokens exist (`clobTokenIds`)
- Market data (volume, order book) is observable

In research mode, markets may be included even if:

- `restricted == true`

### 3.2 Exclusion Criteria

Markets are excluded if:

- No observable liquidity
- No exit path can be modeled
- Outcome resolution is undefined or contradictory
- The market structure prevents fair execution (e.g. no order book)

## 4. Liquidity and Exit Feasibility

### 4.1 Capital-Aware Research

All research is conducted relative to a notional capital size.

**Key quantities:**
- Target position size `S`
- 24h traded volume
- Top-of-book and depth (Depth5 proxy)

### 4.2 Exit Risk Definition

Exit Risk is defined as:

```
ExitRisk = PositionSize / Volume24h
```

Research rejects markets where:

- Expected exit would dominate daily volume
- Forced liquidation would materially move price

This prevents false alpha that only exists at infinitesimal size.

## 5. Market Regime Classification (BotScore)

### 5.1 Motivation

Prediction markets exhibit regime heterogeneity:

- Some are bot-dominated and mechanical
- Others are narrative- and belief-driven

**Strategies are only valid in their appropriate regime.**

### 5.2 BotScore V0

BotScore is computed from observable proxies:

- Quote churn intensity
- Price movement per unit volume
- Order book symmetry
- Update-to-trade ratios

Markets are classified as:

- **BOT**
- **HUMAN**
- **MIXED**

This classification is descriptive, not predictive.

## 6. Strategy Research Families

### 6.1 A* — Automated / Microstructure Strategies

**Hypothesis:** In bot-dominated markets, short-term price moves are often caused by liquidity mechanics, not information.

**Observable phenomena:**
- Depth collapses
- Spread explosions
- High price movement with low traded volume

**Research objective:**
- Detect mechanical dislocations
- Measure mean reversion probability
- Quantify slippage and adverse selection

### 6.2 H* — Human / Informational Strategies

**Hypothesis:** In human-driven markets, mispricings arise from:

- Wording ambiguity
- Incorrect scenario weighting
- Misunderstanding of resolution rules

**Research objective:**
- Construct scenario trees
- Compare implied vs modeled probabilities
- Measure convergence dynamics

## 7. Signal Validation

### 7.1 Paper Trading Only

All signals are first evaluated in paper mode:

- No execution assumptions are hidden
- Slippage is modeled conservatively
- Partial fills are assumed

### 7.2 Required Statistics

A strategy is considered viable only if:

- Positive expected value across multiple markets
- Stable performance across time slices
- No dependency on single events or anomalies
- Drawdowns are bounded and explainable

## 8. Research Output

Research outputs include:

- Signal logs
- Regime-labeled market datasets
- PnL attribution by strategy and regime
- Failure case analysis

> Only after sustained validation does a strategy become a candidate for execution.

## 9. What This Methodology Explicitly Avoids

- Narrative-only trading
- Overfitting to resolved outcomes
- Ignoring liquidity constraints
- Ignoring regulatory reality
- Treating prediction markets like equities

## 10. Research Integrity

All research must be:

- **Reproducible** from raw data
- **Explainable** without hindsight
- **Robust** to market participation changes
