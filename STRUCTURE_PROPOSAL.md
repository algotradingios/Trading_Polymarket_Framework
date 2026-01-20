# Project Structure Proposal

## Current Issues Identified

### 1. **Flat Structure**
- All Python files in root directory (18 files)
- No clear separation of concerns
- Difficult to navigate and understand dependencies

### 2. **Code Duplication**
- `screening.py` and `microstructure.py` have identical functions
- `data_clients.py` and `providers.py` have overlapping functionality
- `config.py` and `settings.py` have overlapping concerns
- `run_v0.py` appears to be legacy code

### 3. **Mixed Concerns**
- Data access mixed with business logic
- Domain models scattered across files
- Strategies not clearly separated
- Entry points unclear (multiple `run_*.py` files)

### 4. **Configuration Issues**
- `settings.py` has duplicate `EQUITY` and `TARGET_POS_FRAC` fields
- `engine_research.py` has hardcoded API hosts (should use settings)

## Proposed Structure

```
polymarket_framework/
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Single source of truth for all configuration
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── clients.py           # Unified data access (merge providers.py + data_clients.py)
│   │   └── models.py            # Domain models (MarketMeta, MarketSnapshot, etc.)
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── screening.py         # Screening engine (screening_engine.py)
│   │   ├── microstructure.py    # Microstructure utilities (merge screening.py into this)
│   │   └── bot_score.py         # Bot score classification
│   │
│   ├── strategies/
│   │   ├── __init__.py
│   │   ├── base.py              # Base strategy interface (optional)
│   │   ├── a2_cascade.py        # A2 cascade detector (a2_detector.py)
│   │   └── h1_informational.py  # H1 checklist (h1_checklist.py)
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   └── store.py             # SQLite storage (store.py)
│   │
│   └── execution/
│       ├── __init__.py
│       └── adapter.py           # Execution adapter (execution_adapter.py)
│
├── scripts/
│   ├── __init__.py
│   ├── research_engine.py       # Main research loop (engine_research.py)
│   ├── screening.py             # Screening script (run_screening_v1.py)
│   └── diagnostics.py           # Diagnostic tools (gamma_sanity.py, data_audit.py)
│
├── tests/
│   └── __init__.py
│
├── docs/
│   ├── README.md
│   ├── RESEARCH_METHODOLOGY.md
│   └── DEPLOYMENT_GUIDE.md
│
├── pyproject.toml
├── uv.lock
├── LICENSE
└── .gitignore
```

## Detailed Migration Plan

### Phase 1: Create Directory Structure

1. Create `src/` directory with subdirectories:
   - `config/`
   - `data/`
   - `domain/`
   - `strategies/`
   - `storage/`
   - `execution/`

2. Create `scripts/` directory for entry points

3. Create `tests/` directory for future tests

4. Create `docs/` directory and move markdown files

### Phase 2: Consolidate and Move Files

#### Config Layer
- **`src/config/settings.py`**
  - Fix duplicate `EQUITY` and `TARGET_POS_FRAC`
  - Single source of truth for all configuration
  - Remove `config.py` (merge useful parts into settings)

#### Data Layer
- **`src/data/models.py`**
  - Move domain models: `MarketMeta`, `MarketSnapshot`, `OrderBookTopK`
  - Add any other data models

- **`src/data/clients.py`**
  - Merge `providers.py` and `data_clients.py`
  - Keep `MarketDataProvider` as the main interface
  - Remove duplicate `GammaClient` and `ClobPublic` implementations

#### Domain Layer
- **`src/domain/microstructure.py`**
  - Merge `microstructure.py` and `screening.py` (they're identical)
  - Keep all microstructure utility functions

- **`src/domain/screening.py`**
  - Rename `screening_engine.py` → `screening.py`
  - Move `ScreeningConfig`, `ScreeningResult`, `ScreeningEngine`

- **`src/domain/bot_score.py`**
  - Move `bot_score.py` as-is

#### Strategies Layer
- **`src/strategies/a2_cascade.py`**
  - Rename `a2_detector.py` → `a2_cascade.py`
  - Move A2 detector logic

- **`src/strategies/h1_informational.py`**
  - Rename `h1_checklist.py` → `h1_informational.py`
  - Move H1 checklist logic

#### Storage Layer
- **`src/storage/store.py`**
  - Move `store.py` as-is

#### Execution Layer
- **`src/execution/adapter.py`**
  - Rename `execution_adapter.py` → `adapter.py`
  - Move execution adapter

#### Scripts Layer
- **`scripts/research_engine.py`**
  - Rename `engine_research.py` → `research_engine.py`
  - Fix hardcoded API hosts to use settings
  - Update imports

- **`scripts/screening.py`**
  - Rename `run_screening_v1.py` → `screening.py`
  - Update imports

- **`scripts/diagnostics.py`**
  - Merge `gamma_sanity.py` and `data_audit.py` into one diagnostics module
  - Or keep separate but in scripts/

- **Remove:**
  - `run_v0.py` (legacy)
  - `main.py` (placeholder, not needed)
  - `screening.py` (duplicate of microstructure.py)
  - `data_clients.py` (merged into data/clients.py)
  - `config.py` (merged into config/settings.py)

### Phase 3: Update Imports

Update all import statements to reflect new structure:

```python
# Old
from providers import MarketDataProvider
from screening_engine import ScreeningEngine
from settings import SETTINGS

# New
from polymarket_framework.data.clients import MarketDataProvider
from polymarket_framework.domain.screening import ScreeningEngine
from polymarket_framework.config.settings import SETTINGS
```

### Phase 4: Update pyproject.toml

Add package configuration:

```toml
[project]
name = "polymarket-framework"
# ... existing config ...

[tool.setuptools]
packages = ["polymarket_framework"]

[tool.setuptools.package-dir]
"" = "src"
```

## Benefits of New Structure

1. **Clear Separation of Concerns**
   - Data access isolated from business logic
   - Strategies clearly separated
   - Storage abstracted
   - Execution isolated

2. **Better Maintainability**
   - Easy to find related code
   - Clear dependencies
   - Reduced duplication

3. **Easier Testing**
   - Each layer can be tested independently
   - Clear interfaces between layers

4. **Scalability**
   - Easy to add new strategies
   - Easy to add new data sources
   - Easy to swap storage backends

5. **Professional Structure**
   - Follows Python packaging best practices
   - Clear entry points
   - Proper namespace management

## Migration Checklist

- [ ] Create directory structure
- [ ] Fix settings.py duplicate fields
- [ ] Consolidate data clients
- [ ] Merge duplicate microstructure files
- [ ] Move files to new locations
- [ ] Update all imports
- [ ] Update pyproject.toml
- [ ] Update README with new structure
- [ ] Test all scripts still work
- [ ] Remove legacy files
- [ ] Update .gitignore if needed

## Entry Points After Migration

```bash
# Main research engine
uv run python -m scripts.research_engine

# Screening script
uv run python -m scripts.screening

# Diagnostics
uv run python -m scripts.diagnostics
```

Or create console scripts in pyproject.toml:

```toml
[project.scripts]
polymarket-research = "scripts.research_engine:main"
polymarket-screening = "scripts.screening:main"
polymarket-diagnostics = "scripts.diagnostics:main"
```

Then use:
```bash
polymarket-research
polymarket-screening
polymarket-diagnostics
```
