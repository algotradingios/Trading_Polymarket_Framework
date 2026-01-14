# Deployment Guide

## Purpose

This document explains how the framework is intended to be deployed, with a strict separation between:

- **Research environments**
- **Execution environments**

It also documents geographic and regulatory constraints that affect deployment.

## 1. Deployment Modes

The framework supports two explicit modes:

- `MODE = research`
- `MODE = execution`

> These modes are mutually exclusive.

## 2. Research Deployment (Default)

### 2.1 Intended Use

Research deployment is designed for:

- Spain / EU
- UK
- US
- Any restricted jurisdiction

### 2.2 Capabilities

In research mode, the framework can:

- Access Gamma API market metadata
- Read CLOB order books and prices
- Compute signals and regimes
- Simulate execution and PnL
- Log all outputs

### 2.3 Restrictions

In research mode:

- **No orders are placed**
- **No signatures are generated**
- **No wallets are required**

This mode is fully compliant with geographic restrictions.

### 2.4 Typical Architecture

```
Local Machine / Research Server
│
├── Universe Builder
├── Screening Engine
├── BotScore
├── Strategy Signals
└── Paper PnL Logger
```

## 3. Execution Deployment (Optional)

### 3.1 Preconditions

Execution mode requires:

- A jurisdiction where Polymarket allows trading
- A compliant runtime environment
- A non-custodial wallet
- Explicit user opt-in

> **If any of these are missing, execution must not be enabled.**

### 3.2 Execution Adapter Pattern

Execution is isolated behind an adapter:

```python
class ExecutionAdapter:
    def place_order(...)
```

**In research mode:**
```python
raise NotImplementedError
```

**In execution mode:**
- Signs orders
- Submits to CLOB
- Handles confirmations and errors

### 3.3 Recommended Architecture

```
Research Engine (anywhere)
        │
        ▼
Signal File / Queue (JSON, DB, Kafka)
        │
        ▼
Execution Engine (permitted jurisdiction)
        │
        ▼
Polymarket CLOB
```

This architecture ensures:

- **Auditability**
- **Legal separation**
- **Operational robustness**

## 4. Geographic Restrictions (Critical)

### 4.1 Observed Behavior

From Spain and most of the EU:

- `restricted == true` for all liquid markets
- Order placement is blocked
- Read-only access is permitted

### 4.2 Framework Response

The framework:

- **Does not bypass restrictions**
- **Does not obfuscate location**
- **Does not attempt unauthorized execution**

> Execution is only possible if the runtime environment is permitted.

## 5. Configuration Flags

**Typical configuration:**

```python
ALLOW_RESTRICTED = True     # research
EXECUTION_ENABLED = False  # default
```

**Execution deployment requires:**

```python
ALLOW_RESTRICTED = False
EXECUTION_ENABLED = True
```

## 6. Operational Risk Management

Execution deployments must include:

- Max exposure per market
- Daily loss limits
- Kill switches
- Monitoring of order rejections
- Immediate disablement on API errors

## 7. What This Framework Does NOT Do

- Circumvent geographic restrictions
- Hide user identity or location
- Provide legal or financial advice
- Guarantee profitability

## 8. Final Remarks

This framework is designed to:

- Enable serious quantitative research on prediction markets
- Remain deployable without refactoring
- Respect regulatory boundaries
- Scale from analysis to execution when allowed

If you later want:

- A paper-trading backtester aligned with live signals
- A formal risk policy document
- Or a production execution checklist

Those can be added naturally on top of this structure.
