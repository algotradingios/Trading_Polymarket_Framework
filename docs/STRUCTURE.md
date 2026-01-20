# Project Structure

This document describes the organization of the Polymarket Quantitative Research Framework.

## Directory Layout

```
polymarket_framework/
├── src/                    # Main package code
│   ├── config/            # Configuration
│   ├── data/              # Data access layer
│   ├── domain/            # Business logic
│   ├── strategies/        # Strategy implementations
│   ├── storage/           # Data persistence
│   └── execution/         # Execution layer
├── scripts/               # Executable scripts
├── docs/                  # Documentation
├── tests/                 # Test suite (ready for tests)
├── pyproject.toml         # Project configuration
└── uv.lock                # Dependency lock file
```

## Package Structure (`src/`)

### `config/` - Configuration
- **`settings.py`**: Centralized configuration with all framework settings
  - Mode toggles (ALLOW_RESTRICTED, EXECUTION_ENABLED)
  - API configuration (GAMMA_HOST, CLOB_HOST, CHAIN_ID)
  - Capital assumptions (EQUITY, TARGET_POS_FRAC)
  - Polling parameters (PAGES, LIMIT, SLEEP intervals)
  - Strategy parameters (A2 detector params)
  - Storage configuration (SQLITE_PATH)

### `data/` - Data Access Layer
- **`models.py`**: Domain models
  - `MarketMeta`: Market metadata from Gamma API
  - `MarketSnapshot`: Snapshot of market state (prices, depth, volume)
  - `OrderBookTopK`: Order book structure
- **`clients.py`**: API clients
  - `GammaClient`: Polymarket Gamma API client
  - `ClobPublic`: CLOB (order book) API client
  - `MarketDataProvider`: High-level provider combining both APIs

### `domain/` - Business Logic
- **`screening.py`**: Liquidity and exit feasibility screening
  - `ScreeningConfig`: Configuration for screening thresholds
  - `ScreeningEngine`: Engine that screens markets based on capital constraints
  - `ScreeningResult`: Result of screening operation
- **`bot_score.py`**: Market regime classification
  - `BotScoreInputs`: Inputs for bot score calculation
  - `botscore_v0()`: Calculate bot score from snapshot data
  - `regime_from_score()`: Convert bot score to regime (BOT/HUMAN/MIXED)
- **`microstructure.py`**: Microstructure utility functions
  - `depth5_notional()`: Calculate depth proxy from order book
  - `best_bid_ask()`: Extract best bid/ask from order book
  - `book_symmetry()`: Calculate order book symmetry

### `strategies/` - Strategy Implementations
- **`a2_cascade.py`**: A2 cascade detection strategy
  - `A2State`: State tracking for cascade detection
  - `A2Params`: Parameters for cascade detection
  - `A2Signal`: Signal output from cascade detector
  - `a2_detect()`: Main cascade detection function
- **`h1_informational.py`**: H1 informational strategy framework
  - `H1Case`: Case data for H1 evaluation
  - `H1Decision`: Decision output from H1 checklist
  - `H1Checklist`: Checklist-based evaluation engine

### `storage/` - Data Persistence
- **`store.py`**: SQLite storage layer
  - `Store`: Main storage class
  - `SnapshotRow`: Row structure for snapshots table
  - `BotScoreRow`: Row structure for bot_scores table
  - `SignalRow`: Row structure for signals table

### `execution/` - Execution Layer
- **`adapter.py`**: Execution adapter (disabled by default)
  - `ExecutionAdapter`: Adapter for order placement
  - `OrderIntent`: Intent structure for orders
  - Note: Execution is disabled in research mode

## Scripts (`scripts/`)

### `research_engine.py`
Main research loop that:
- Fetches market universe
- Takes snapshots of market state
- Applies screening and bot score classification
- Detects A2 cascade signals
- Stores results in database
- Runs continuously with configurable sleep intervals

**Usage:**
```bash
uv run python -m scripts.research_engine
```

### `screening.py`
One-time screening script that:
- Fetches market universe
- Applies screening for both A* and H* strategies
- Reports which markets pass screening criteria

**Usage:**
```bash
uv run python -m scripts.screening
```

### `diagnostics.py`
Diagnostic tool that:
- Tests Gamma API connectivity
- Reports market statistics (restricted, closed, archived)
- Helps verify environment configuration

**Usage:**
```bash
uv run python -m scripts.diagnostics
```

## Import Patterns

### Option 1: Import from package root
```python
from src import SETTINGS, MarketDataProvider, ScreeningEngine
```

### Option 2: Import from specific modules
```python
from src.config.settings import SETTINGS
from src.data.clients import MarketDataProvider
from src.domain.screening import ScreeningEngine
```

### Option 3: Import from sub-packages
```python
from src.data import MarketDataProvider, MarketMeta
from src.domain import ScreeningEngine, botscore_v0
from src.strategies import A2State, a2_detect
```

## Design Principles

1. **Separation of Concerns**: Each layer has a clear responsibility
2. **Research-First**: All code works in research mode without execution
3. **Capital-Aware**: All screening is relative to capital size
4. **Regime-Aware**: Strategies are matched to market regimes
5. **Explicit Configuration**: All settings centralized in `settings.py`

## Adding New Components

### Adding a New Strategy
1. Create file in `src/strategies/`
2. Implement strategy logic
3. Add exports to `src/strategies/__init__.py`
4. Update `src/__init__.py` if needed
5. Integrate into `scripts/research_engine.py`

### Adding a New Data Source
1. Add client to `src/data/clients.py` or create new client file
2. Add models to `src/data/models.py` if needed
3. Update `MarketDataProvider` to use new client
4. Export from `src/data/__init__.py`

### Adding New Storage Backend
1. Create new file in `src/storage/`
2. Implement same interface as `Store` class
3. Update `scripts/research_engine.py` to use new backend
4. Export from `src/storage/__init__.py` if created
