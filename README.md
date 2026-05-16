# HedgeFund-Like Stock Screener

## Purpose

HedgeFund-Like is designed to become a desktop stock screener and research assistant for finding, filtering, and comparing public companies before doing a deeper manual review.

The app is intended to combine company fundamentals, market data, readiness scoring, watchlist organization, flagging, and peer comparison into one workflow.

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
- Applying high-level flags for valuation, quality, balance sheet strength, dilution risk, and data confidence.
- Comparing companies against relevant peer groups.
- Separating raw calculation data from readable screening views.

## Core Design Goal

The app is not meant to be a buy/sell signal.

It is meant to be a first-pass screening system that helps identify which companies are worth deeper research and which companies should be skipped, watched, or investigated further.

## Planned Workflow

1. Add or select a ticker.
2. Enter required API credentials.
3. Refresh SEC data.
4. Refresh Finnhub data.
5. Normalize market data.
6. Calculate readiness.
7. Review the ticker in the Master Watchlist.
8. Check flags and peer comparison.
9. Decide whether the company deserves deeper manual research.

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
