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
- Dedicated historical fundamentals table populated from SEC annual companyfacts rows.
- Finnhub daily candle pull with local price-history storage.
- Yahoo Chart fallback for daily price history when the Finnhub candle endpoint is unavailable or not included with the saved key.
- Standalone SEC-history rebuild and price-history refresh actions.
- Repair Missing Data action that rebuilds cached SEC history, recalculates existing price metrics, refreshes Finnhub price history when an API key is available, then renormalizes market data and readiness.
- Price Trend view with 52-week high/low, returns, drawdown, momentum, and volatility metrics.
- Historical Fundamentals and Price History UI views.
- Score Details view that explains each ticker's data, quality, valuation, balance-sheet, dilution, and FCF scores.
- Color-coded score and flag cells so high-potential, watchlist, warning, and weak names are easier to scan.
- Data Quality view that marks key fields as complete, partial, stale, or missing with suggested repair actions.
- Data Quality warning for non-USD SEC units that can distort valuation multiples for foreign issuers.
- High-level valuation, quality, balance sheet, dilution, FCF, and data-confidence flags.
- Partial support for foreign issuers using IFRS SEC companyfacts.
- DEI share-count fallback for historical dilution when standard share concepts are incomplete.
- Larger custom scrollbars.
- Dark premium dashboard UI.
- Functional top navigation.
- Slimmer polished scrollbars and cleaner tab button styling.
- Draggable workspace tabs with locally saved custom tab order.
- Polished HTML Overview HUD with colored signal tiles, score badges, decision buckets, and research alerts.
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

If a view is empty after a data pull, use **Repair Missing Data**. It will use cached SEC rows first, then stored price candles, then Finnhub or the Yahoo Chart fallback when the missing view depends on price history that has never been downloaded.

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

Partially added: the app now has a dedicated `historical_fundamentals` table rebuilt from SEC annual companyfacts rows after SEC refreshes.

Still needed:

- More complete balance-sheet history where SEC companyfacts coverage is partial.
- Historical balance-sheet trend calculations.
- UI drill-downs that explain which SEC concept supplied each historical value.
- Stronger handling of restatements and duplicate annual facts.

### 2. Historical price data

Partially added: the app now pulls Finnhub daily candles during Finnhub/full pipeline refreshes, falls back to Yahoo Chart when Finnhub candles are unavailable, stores daily rows in `price_history`, and derives `price_metrics`.

Still needed:

- Better adjusted-close support if a provider exposes split/dividend-adjusted series separately.
- Charting or sparkline UI for price history.
- More configurable price trend windows.
- Optional second fallback price provider if both Finnhub and Yahoo Chart coverage are unavailable or rate-limited.

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

Partially added: the app now has a Data Quality view that checks key screening fields, freshness, source category, missing/partial/stale status, and suggested repair actions.

Still needed:

- Per-field source confidence.
- Per-field source priority rules.
- UI filter for tickers with weak or incomplete data.
- Data-quality summary score by ticker.
- Better distinction between calculated, derived, estimated, and directly reported values.

### 5. Better scoring transparency

Partially added: the app now has a Score Details view with component scores, weights, weighted points, flags, and readable input/rationale text.

Still needed:

- Add drill-down views for valuation, quality, balance sheet, dilution, and FCF scores.
- Add scoring version labels so future model changes are trackable.
- Add detailed rule-by-rule point attribution for each score component.

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

Partially added: the app now has a richer Overview HUD, color-coded score/flag surfaces, improved table selection behavior, slimmer scrollbars, and cleaner tab styling.

Still needed:

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
