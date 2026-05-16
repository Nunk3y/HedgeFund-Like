# HedgeFund-Like Stock Screener

## Purpose

HedgeFund-Like is designed to become a desktop stock screener and research assistant for finding, filtering, and comparing public companies before doing a deeper manual review.

The app is intended to combine company fundamentals, market data, readiness scoring, watchlist organization, flagging, and peer comparison into one workflow.

## Core Design Goal

The app is not meant to be a buy/sell signal.

It is meant to be a first-pass screening system that helps identify which companies are worth deeper research and which companies should be skipped, watched, or investigated further.

## Current App Status

The app currently supports:

- Desktop UI built with PySide6.
- Watchlist management.
- Peer group assignment.
- SEC companyfacts data pulls.
- Finnhub quote, profile, and metric pulls.
- Local SQLite cache for retrieved API data.
- Local-only API credential storage in `tech_screener.db`.
- SEC User-Agent saving locally, separate from GitHub.
- Normalized market-data layer.
- Model readiness scoring.
- Master Watchlist screening view.
- Peer Comparison view.
- API Cache view.
- Market Data view.
- Model Readiness view.
- High-level valuation, quality, balance sheet, dilution, FCF, and data-confidence flags.
- Partial support for foreign issuers using IFRS SEC companyfacts.
- DEI share-count fallback for historical dilution when standard share concepts are incomplete.
- Larger custom scrollbars.
- Dark premium dashboard UI.
- Functional top navigation.
- A ticker label in wide tables so row context is easier to track while horizontally scrolling.

## Planned Workflow

1. Add or select a ticker.
2. Assign a peer group.
3. Enter required API credentials locally.
4. Run the full pipeline.
5. Pull SEC data.
6. Pull Finnhub data.
7. Normalize market data.
8. Calculate readiness.
9. Review the ticker in the Master Watchlist.
10. Check flags and peer comparison.
11. Decide whether the company deserves deeper manual research.

## Intended End State

The finished app should help screen stocks by:

- Adding and managing tickers in a watchlist.
- Pulling company and financial data from SEC sources.
- Pulling market, profile, and metric data from Finnhub.
- Saving retrieved API data into a local SQLite cache.
- Normalizing SEC and Finnhub data into a consistent market-data layer.
- Calculating model/readiness status for each ticker.
- Displaying a readable Master Watchlist for screening.
- Showing missing, weak, or incomplete data areas.
- Applying high-level flags for valuation, quality, balance sheet strength, dilution risk, FCF strength, and data confidence.
- Comparing companies against relevant peer groups.
- Separating raw calculation data from readable screening views.

## Still Needs To Be Added

### 1. Proper historical data layer

The app needs a dedicated historical-data model instead of relying only on latest normalized values and API-cache rows.

Needed additions:

- Dedicated historical fundamentals table.
- Dedicated historical price table.
- Multi-year revenue, gross profit, operating income, net income, FCF, cash, debt, shares, and dilution history.
- Historical growth-rate calculations.
- Historical margin trend calculations.
- Historical balance-sheet trend calculations.
- Clear separation between latest snapshot metrics and multi-year history.

### 2. Historical price data

The app still needs real historical market-price support.

Needed additions:

- Finnhub daily candle pull.
- Local storage for open, high, low, close, adjusted close, and volume.
- Configurable lookback period.
- 52-week and multi-year trend calculations from stored candles.
- Price momentum flags.
- Drawdown-from-high calculations.
- Basic volatility calculations.

### 3. Better foreign issuer handling

Foreign issuers such as TSM can report differently than U.S. domestic filers.

Needed additions:

- More IFRS concept mappings.
- Better handling for companies reporting in non-USD currencies.
- Currency normalization or explicit currency warnings.
- ADR/share-count conversion awareness.
- Clear warnings when SEC data is partial because of foreign issuer reporting differences.
- Better disclosure notes for partial SBC, R&D, and SG&A coverage.

### 4. Stronger data quality system

The app needs a more formal data-quality layer.

Needed additions:

- Per-field source confidence.
- Per-field freshness checks.
- Per-field source priority rules.
- Clear distinction between missing, partial, estimated, stale, and complete data.
- UI filter for tickers with weak or incomplete data.
- Data-quality summary by ticker.

### 5. Better scoring transparency

The current scoring should become easier to inspect and trust.

Needed additions:

- Explain how each score is calculated.
- Show score inputs in the UI.
- Show why each flag was assigned.
- Add drill-down views for valuation, quality, balance sheet, dilution, and FCF scores.
- Add scoring version labels so future model changes are trackable.

### 6. Peer group improvements

Peer comparison is useful, but still needs refinement.

Needed additions:

- Better default peer-group templates.
- Peer-group editor.
- Automatic peer suggestions.
- Peer median and percentile ranks for more fields.
- Outlier detection so one bad peer does not distort the comparison.
- Option to exclude specific peers from a comparison.

### 7. Dashboard and UI improvements

The UI has improved, but it still needs a more polished production-level table experience.

Needed additions:

- Better sticky/frozen ticker column implementation.
- Cleaner handling of large empty table space.
- Better table column sizing presets.
- Saved column widths.
- Saved layout preferences.
- Better selected-row styling.
- Better detail panel layout.
- Better loading/progress indicators during full pipeline runs.
- Cleaner error messages when API pulls fail.

### 8. Local settings and privacy hardening

The app should stay local-first and avoid pushing private data to GitHub.

Needed additions:

- Confirm `tech_screener.db` remains ignored by Git.
- Confirm all local settings files are ignored by Git.
- Add a setup check that warns if private local files are accidentally tracked.
- Optional local settings export/import.
- Better API-key masking in the UI.

### 9. Testing and verification

The project needs tests before heavier refactors.

Needed additions:

- Unit tests for SEC concept mapping.
- Unit tests for Finnhub response mapping.
- Unit tests for normalization.
- Unit tests for readiness scoring.
- Unit tests for peer comparison.
- Regression tests for foreign issuers such as TSM.
- Smoke test for launching the PySide app.

### 10. Packaging and release workflow

The app still needs a cleaner install/run process.

Needed additions:

- Clear setup instructions.
- Clear `.env` or local-settings guidance if used later.
- Windows launch script.
- Optional packaged desktop build.
- Versioned releases.
- Stable Git tags for usable checkpoints.

## Do Not Add Yet

These should not be added until the data pipeline and scoring are more stable:

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
- Do not fake missing financial data.
- If data is partial, stale, or unavailable, mark it clearly.
- Keep raw API/cache views separate from readable screening views.

## Baseline

This repository is the starting baseline for the project.

Future work should be developed from this point forward using Git commits for meaningful changes and tags for stable save points.

Recommended workflow:

```bash
git status
git add .
git commit -m "Save baseline"
git tag v1
```
