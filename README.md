# HedgeFund-Like Stock Screener

## Purpose

HedgeFund-Like is a local-first desktop stock screener and research assistant for organizing a watchlist, pulling public-company data, comparing companies against peers, and deciding which names deserve deeper manual research.

The app is not a buy/sell signal. It is a first-pass analyst tool.

The app should help answer:

1. Is the ticker data complete enough to trust?
2. How does the company score on quality, valuation, balance sheet, dilution, FCF, price trend, and peer comparison?
3. Which names deserve deeper research?
4. Which names should be watched, passed, or fixed because data is weak?

## Current App Status

The app currently supports:

- Desktop UI built with PySide6.
- Local SQLite storage.
- No default starter tickers. New databases start empty.
- Watchlist management.
- Peer group assignment.
- Searchable watchlist control area.
- SEC User-Agent field with format help.
- Finnhub API-key field with local-only storage.
- Separate local storage for personal settings/API credentials.
- SEC companyfacts pulls.
- Finnhub quote, profile, metric, and candle pulls.
- Yahoo Chart fallback for daily price history when Finnhub candles are unavailable.
- Local raw API cache.
- Normalized market-data layer.
- Historical fundamentals table from SEC annual companyfacts rows.
- Price history table.
- Price trend metrics: 52-week high/low, returns, drawdown, momentum, and volatility.
- Model readiness scoring.
- Master Watchlist screening view.
- Score Details view.
- Data Quality view.
- Peer Comparison view.
- Data Details tab that groups raw/bulk data views.
- Research Guide tab.
- Full pipeline for one selected ticker.
- Full pipeline for all active tickers.
- Dark local-first dashboard UI.

## Local Data Files

The app uses two local database files:

| File | Purpose | Safe to delete? |
|---|---|---|
| `tech_screener.db` | Watchlist, tickers, peer groups, SEC/Finnhub cache, market data, historical fundamentals, price history, readiness/scoring data | Deletes stock/research data only |
| `personal_settings.db` | SEC User-Agent, Finnhub API key, app settings | Deletes API/personal settings only |

Both files are local-only and ignored by Git through `*.db` rules.

Do not commit database files, API keys, caches, logs, virtual environments, or generated build outputs.

## Current Workflow

The UI workflow should follow the Research Guide order:

1. **Overview**
2. **Master Watchlist**
3. **Score Details**
4. **Data Quality**
5. **Peer Comparison**
6. **Data Details**
7. **Research Guide**

`Data Details` groups the bulk/raw tables:

1. Historical Fundamentals
2. Price Trends
3. Price History
4. API Cache
5. Model Readiness
6. Market Data

The left-side action panel should only show:

- Add / Update Ticker
- Run Full Pipeline
- Run Full Pipeline For All Active
- Save API Settings
- Delete Selected Ticker

The old separate buttons should stay removed from the visible UI:

- Repair Missing Data
- Rebuild SEC History
- Refresh Price History

Those operations should be handled by the full pipeline instead of being separate primary actions.

## Basic Use

1. Add a ticker.
2. Assign a peer group.
3. Enter SEC User-Agent in this format:

```text
Your Name your-email@example.com
```

Example:

```text
Sebastiaan Vriese savriese@gmail.com
```

4. Enter Finnhub API key.
5. Run **Run Full Pipeline** for the selected ticker, or **Run Full Pipeline For All Active** for the whole active watchlist.
6. Review the ticker through the workflow tabs in order.
7. Use the Research Guide before deciding whether a ticker deserves a full manual memo.

## Pipeline Scope

The full pipeline should handle:

1. SEC data refresh.
2. Historical fundamentals rebuild.
3. Finnhub data refresh.
4. Price history refresh.
5. Market-data normalization.
6. Model readiness calculation.
7. Table refresh.

The goal is to avoid separate manual repair/rebuild/refresh buttons unless they are hidden developer/debug tools.

## Current Design Rules

- Keep the app local-first.
- Keep private data out of GitHub.
- Keep one active launch path.
- Avoid unused wrapper UI files.
- Avoid stacking messy one-off UI files.
- Make the visible workflow follow the Research Guide.
- Keep raw/bulk data views grouped under `Data Details`.
- Keep readable screening views separate from raw data tables.
- Do not fake missing financial data.
- If data is partial, stale, unavailable, or currency-distorted, mark it clearly.
- Do not turn the app into broker integration, auto-trading, or buy/sell recommendations.

## Still Needs To Be Done

### 1. Clean code structure

The active app currently uses a streamlined launch path in `main.py` that subclasses the base UI. This works, but the long-term cleanup should be to move the streamlined UI code into a proper module and remove dead/unused UI paths.

Needed:

- Keep only one real app window class.
- Move active UI customization out of `main.py` once stable.
- Remove old visible-button logic from base UI if it is no longer used.
- Keep `main.py` small: import the app class and launch it.
- Confirm there are no unused wrapper files.

### 2. UI polish

Needed:

- Make workflow tabs auto-size cleanly at different window widths.
- Keep tab names readable without clipping.
- Improve table column sizing presets.
- Save column widths.
- Save useful layout preferences without fighting the Research Guide workflow order.
- Improve loading/progress indicators during long full-pipeline runs.
- Improve error messages when API pulls fail.
- Make confirmation dialogs readable in dark mode without breaking launch.

### 3. Data quality and transparency

Needed:

- Per-field source confidence.
- Per-field source priority rules.
- Better distinction between reported, calculated, derived, estimated, and missing values.
- Better UI filtering for weak/incomplete data.
- More detailed data-quality summary by ticker.
- More explicit warnings for non-USD SEC units and ADR/foreign issuer issues.

### 4. Historical fundamentals

Partially added: `historical_fundamentals` is rebuilt from SEC annual companyfacts rows.

Still needed:

- More complete balance-sheet history where SEC coverage is partial.
- Historical balance-sheet trend calculations.
- Drill-downs showing which SEC concept supplied each historical value.
- Stronger restatement/duplicate annual fact handling.

### 5. Historical price data

Partially added: daily price candles are stored in `price_history`, and derived metrics are stored in `price_metrics`.

Still needed:

- Better adjusted-close support.
- Charting or sparkline UI.
- More configurable trend windows.
- Optional second fallback provider if Finnhub and Yahoo are unavailable or rate-limited.

### 6. Foreign issuer handling

Needed:

- More IFRS concept mappings.
- Better handling of non-USD reporting.
- Currency normalization or stronger currency warnings.
- ADR/share-count conversion awareness.
- Better disclosure notes for partial SBC, R&D, SG&A, and share-count coverage.

### 7. Scoring transparency

Partially added: Score Details explains component scores and rationale.

Still needed:

- Scoring version labels.
- Rule-by-rule point attribution.
- More detailed drill-downs for valuation, quality, balance sheet, dilution, and FCF.

### 8. Peer group improvements

Needed:

- Better default peer-group templates.
- Peer-group editor.
- Automatic peer suggestions.
- More peer median and percentile ranks.
- Outlier detection.
- Option to exclude specific peers from comparison.

### 9. Privacy hardening

Needed:

- Startup check that warns if private local files are accidentally tracked by Git.
- Confirm `.db`, cache, log, build, and virtual environment files remain ignored.
- Optional local settings export/import.
- Better API-key masking.

### 10. Testing and release workflow

Needed:

- Unit tests for SEC concept mapping.
- Unit tests for Finnhub response mapping.
- Unit tests for normalization.
- Unit tests for readiness scoring.
- Unit tests for peer comparison.
- Regression tests for foreign issuers such as TSM.
- Smoke test for launching the PySide app.
- Windows launch script.
- Optional packaged desktop build.
- Versioned releases.
- Stable Git tags for usable checkpoints.

## Do Not Add Yet

Do not add these until the data pipeline and scoring are more stable:

- Automated buy/sell recommendations.
- Broker integration.
- Auto-trading.
- Portfolio allocation advice.
- Complex machine-learning models.
- Cloud sync.
- User accounts.

## Development Rules

Future work should follow these rules:

- Preserve working versions with commits before major changes.
- Prefer small reversible changes.
- Do not delete, move, rename, or rewrite files without first classifying them.
- Keep local data, API keys, databases, caches, logs, virtual environments, and generated outputs out of Git.
- If a generated or local-only file is already tracked, remove it from Git tracking with `git rm --cached <file>` instead of deleting the local file.
- Do not claim a change is complete unless it was committed and verified.
- If search returns nothing, verify another way.
- Keep raw API/cache views separate from readable screening views.

## Run Locally

From the repo folder:

```bash
python main.py
```

Typical update flow:

```bash
git pull origin main
python main.py
```

## Baseline / Save Points

Use commits for meaningful changes and tags for stable checkpoints.

Recommended checkpoint workflow:

```bash
git status
git add .
git commit -m "Describe the stable change"
git tag v1.x
```
