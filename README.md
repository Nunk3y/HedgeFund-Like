# Tech Stock Screener Desktop App v4

Adds:
- Finnhub integration
- Refresh Finnhub Data button
- Finnhub market/profile/metric rows saved into SQLite API Cache
- Market Data normalization from SEC + Finnhub
- Model Readiness cleanup for pre-revenue companies like OKLO
- Test support for revenue companies like NVDA

## Workflow

1. Add/select ticker.
2. Enter SEC User-Agent.
3. Enter Finnhub API key.
4. Click:
   - Refresh SEC Data
   - Refresh Finnhub Data
   - Normalize Market Data
   - Calculate Readiness

Or click:
   Run SEC + Finnhub → Market Data → Readiness

## Units

Market Data uses raw calculation units:
- dollar totals = raw dollars
- shares = raw share count
- price/EPS = dollars per share
- ratios = decimals


## v4.1 changes

- Adds Finnhub fallback for revenue using revenue-per-share * shares outstanding.
- If revenue is zero, gross profit is treated as zero instead of ordinary missing.
- Adds Finnhub-derived EBITDA fallback using EBITDA-per-share * shares outstanding.
- OKLO should now show revenue/gross profit as pre-revenue/zero when Finnhub supplies zero revenue per share.
- NVDA should stop showing EBITDA as missing if Finnhub supplies EBITDA per share.


## v4.2 changes

- More robust Finnhub lookup for price, market cap, shares, beta, volume, EPS/P-E.
- Full pipeline now requires a Finnhub key instead of silently skipping Finnhub.
- SEC helper now pulls depreciation/amortization if available.
- EBITDA fallback: operating income + depreciation/amortization.
- Market-cap fallback: price × shares outstanding.


## v5 changes

Adds a Master Watchlist tab.

Master Watchlist is the readable screener layer:
- raw dollar values are displayed as $M / $B
- raw share counts are displayed as millions
- readiness, next action, and missing/weak areas appear beside market and financial fields
- Market Data remains the raw calculation layer
- Master Watchlist is for viewing/screening only

Suggested test:
1. Add OKLO.
2. Run SEC + Finnhub → Market Data → Readiness.
3. Add NVDA.
4. Run SEC + Finnhub → Market Data → Readiness.
5. Open Master Watchlist and compare both rows.


## v6 changes

Adds a first-pass Flag Engine to the Master Watchlist.

New flags:
- Overall Flag
- Deep Dive Action
- Valuation Flag
- Quality Flag
- Balance Sheet Flag
- Dilution Flag
- Data Confidence Flag

Labels:
- GREEN — Deep Dive Candidate
- YELLOW — Watch / Needs Catalyst
- RED — Skip / Too Weak
- GRAY — Insufficient Data
- PURPLE — Speculative Catalyst Only

Important:
This is a first-pass screen, not a buy/sell signal. The next stage should add peer-group medians so valuation flags are based on same-sector comparison instead of rough absolute thresholds.


## v6.1 changes

Master Watchlist flag columns are now color-coded:
- Green = deep dive candidate / strong
- Yellow = watch / mixed
- Red = skip / weak
- Gray = insufficient data
- Purple = speculative catalyst only

Colored columns include:
- Overall Flag
- Deep Dive Action
- Valuation Flag
- Quality Flag
- Balance Sheet Flag
- Dilution Flag
- Data Confidence Flag
- Readiness


## v7 changes

Adds Peer Comparison.

Peer Comparison uses each ticker's Category as its peer group for now.

New tab:
- Peer Comparison

New peer fields:
- Peer Group
- Peer Count
- Overall Peer Flag
- Relative Valuation Flag
- Relative Quality Flag
- Relative Balance Flag
- EV/Revenue vs peer median
- EV/FCF vs peer median
- P/S vs peer median
- FCF margin vs peer median
- operating margin vs peer median
- gross margin vs peer median
- current ratio vs peer median

Important:
A peer group needs at least 2 companies before comparison is meaningful. If a group has only one ticker, the app will show "GRAY — Need More Peers."

Next recommended step:
Add a Peer Group override field so category and peer group can be different.


## v7.1 changes

Category input is now an editable dropdown.

You can choose from preset categories or type your own custom category manually.

Preset examples:
- AI Hardware / Semiconductors
- Semiconductor Manufacturing
- Semiconductor Equipment
- Semiconductor IP
- AI Infrastructure / Servers
- SMR / Nuclear
- Uranium / Nuclear Fuel
- Grid / Electrification
- Robotics / Automation
- Defense Tech
- Space / Satellites
- Quantum Computing
- Cybersecurity
- Cloud / AI Software

Peer Comparison currently uses the Category text as the peer group, so matching category names exactly matters.

## Versioning / Save Points

This repository is used to track edits to the Stock Screener project.

Current baseline: **v1**

Recommended workflow:

```bash
git status
git add .
git commit -m "Describe the save point"
git tag v1.1   # optional named checkpoint
```

Use commits for every meaningful edit and tags for major stable save points.

