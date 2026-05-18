# HedgeFund-Like Stock Screener

## Purpose

HedgeFund-Like is a local-first desktop stock screener and research workflow app for sector-first investors.

The user starts with a sector or theme they already believe may improve, such as AI hardware, data centers, grid infrastructure, robotics, nuclear, fusion-adjacent energy, quantum computing, or other future-tech themes. The app's job is not to re-prove that the broad theme matters. The app's job is to first show which tickers are worth attention, then help decide whether a flagged company is the best public-company vehicle for that theme.

The app is not a buy/sell signal. It is a local research system and decision filter.

The app should help answer:

1. I like this sector, but which companies are flagged by the screener?
2. Why did the app flag this ticker?
3. Are the numbers strong enough to justify more work?
4. Is this ticker better than its closest peers or the sector ETF?
5. Is the future already priced in?
6. What could make this the wrong company to own for the sector?
7. After the data checks, does this ticker actually fit my sector thesis?
8. Should I pass, watch, deep dive more, or treat it as a candidate position?
9. If it becomes a candidate position, how much belongs in the portfolio?

## Core User Philosophy

The app should fit this investing style:

- The user is not trying to be a business-school analyst first.
- The user starts with broad future themes, especially physical technology and infrastructure.
- The user wants the app to flag which companies deserve attention before doing manual research.
- The user does not want to answer manual sector-fit questions before seeing whether the stock is actually flagged and financially interesting.
- Every research step should act as a gate.
- If a gate shows a major problem, the user should be able to stop and move to another ticker.
- The app should not force full analysis of every company.

The app should answer:

```text
Given that I already like this sector, did the screener flag this company for a good reason, and is it the best public-company vehicle for that sector?
```

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
- Model readiness checks.
- Master Watchlist screening view.
- Data Quality view.
- Red Flag and Peer Gate workflow views.
- Peer Comparison view.
- Full pipeline for one selected ticker.
- Full pipeline for all active tickers.
- Dark local-first dashboard UI.
- Screener-first sector workflow in the active `main.py` launch path.

## Local Data Files

The app uses two local database files:

| File | Purpose | Safe to delete? |
|---|---|---|
| `tech_screener.db` | Watchlist, tickers, peer groups, SEC/Finnhub cache, market data, historical fundamentals, price history, readiness, and workflow data | Deletes stock/research data only |
| `personal_settings.db` | SEC User-Agent, Finnhub API key, app settings | Deletes API/personal settings only |

Both files are local-only and ignored by Git through `*.db` rules.

Do not commit database files, API keys, caches, logs, virtual environments, or generated build outputs.

The detailed product workflow spec lives at `docs/product_workflow_spec.txt`. Use that file as the build blueprint for the screener flow and Step 4 risk/reward model.

## Target Workflow

The app should use a screener-first sector workflow, not a generic business-school checklist.

Current target workflow:

0. **Idea Entry**
1. **Data Check**
2. **Red Flag Check**
3. **Peer Gate**
4. **Risk / Reward vs ETF**
5. **Decision / Action**

The app's job is to decide whether a ticker is worth leaving the screener for deeper company research. It should not try to replace the company research memo.

Each decision step should end with one of these results:

```text
Continue
Needs Proof
Pass For Now
```

Meaning:

- **Continue** means the ticker earned the next step.
- **Needs Proof** means the idea is not dead, but the user needs a specific missing proof point before continuing.
- **Pass For Now** means stop researching this ticker and go back to the Sector Funnel or another company.

## Gate Definitions

### 0. Idea Entry

Purpose: pick the ticker to review.

This includes Sector Funnel and Flag Review.

Sector Funnel answers:

```text
Inside this sector/theme, which tickers are worth testing further?
```

Flag Review answers:

```text
Why did the app flag this stock, and is that flag based on clean data?
```

This step should not prove the company is good. It only chooses what deserves the next checks.

### 1. Data Check

Purpose: decide whether the local data is clean enough to compare the ticker against peers.

Main question:

```text
Is the app's data reliable enough for peer comparison?
```

This gate should not decide whether margins, valuation, balance sheet, or dilution are good. Those judgments need peer context. Data Check only catches missing data, weak source coverage, and obvious reliability problems before Peer Gate.

Data Check should include:

- Data Score.
- Missing core data.
- Source quality.
- Peer group assigned or missing.

### 2. Red Flag Check

Purpose: catch obvious danger before peer comparison.

Main question:

```text
Is anything obviously dangerous before we spend more time?
```

Red Flag Check should include:

- Negative free cash flow with short cash runway.
- Extreme dilution.
- Dangerous liquidity.
- Missing core data.
- No peer group assigned.

This step is not trying to find good companies. It only catches obvious reasons to stop or demand proof.

### 3. Peer Gate

Purpose: decide whether this ticker is a better sector vehicle than peers or an ETF.

Main question:

```text
Is this flagged company actually better than the other available choices?
```

This gate compares valuation, quality, balance sheet, dilution, and free-cash-flow strength against the peer group. The app should avoid calling a company "good" from isolated raw numbers alone.

### 4. Risk / Reward vs ETF

Purpose: decide whether the possible upside is worth the downside and better than the ETF alternative.

Main question:

```text
If the company does worse, normal, or better than expected, what could the stock be worth?
```

Risk / Reward should include:

- Bear, base, and bull cases.
- Historical data to estimate business performance assumptions.
- Peer multiples to estimate what the market may pay.
- Four valuation methods: EV/Revenue, EV/FCF, P/E, and DCF.
- Weighted blended value, not a blind average.
- Current-price upside/downside.
- ETF bear/base/bull comparison.

ETF comparison question:

```text
Is the single stock worth the extra risk compared with the easier ETF choice?
```

### 5. Decision / Action

Purpose: summarize the app's checks and decide the next move.

Main question:

```text
Should I leave the screener and do real company research?
```

Decision buckets:

```text
Pass
Watchlist
Deep Dive
Candidate Position
```

Meaning:

- **Pass** means not worth more time right now.
- **Watchlist** means interesting, but needs better price, cleaner data, or a catalyst.
- **Deep Dive** means the ticker earned serious company research outside the screener.
- **Candidate Position** should only happen after deeper research, thesis, valuation, risk, ETF alternative, and kill criteria are clear.

Step 5 should summarize:

```text
Data Check:
Red Flag Check:
Peer Gate:
Risk / Reward vs ETF:
Decision:
Reason:
Next action:
```

## After The Screener

If Step 5 says Deep Dive, the user leaves the screener and starts company research.

Company research belongs in a separate memo/research phase:

- Understand the business.
- Read filings.
- Build or refine valuation assumptions.
- Identify the variant view.
- Write the pre-mortem.
- Decide Pass, Watchlist, or Candidate Position.

Portfolio sizing belongs after a ticker becomes a true Candidate Position.

## Supporting Data Views

Raw/bulk data should not dominate the main navigation. It should support the gate workflow.

Current supporting views:

- Historical Fundamentals
- Market Data
- Model Readiness
- Peer Comparison
- API Cache
- Price Trends
- Price History
- Data Quality

The user should not have to interpret every raw table before moving on. The app should increasingly translate raw data into gate-level decisions.

## Active Action Panel

The left-side action panel should only show:

- Add / Update Ticker
- Run Full Pipeline
- Run Full Pipeline For All Active
- Save API Settings
- Delete Selected Ticker

Advanced maintenance actions should stay out of the primary action panel:

- Repair Missing Data
- Rebuild SEC History
- Refresh Price History

Those operations should be handled by the full pipeline instead of being separate primary actions.

## Basic Use

1. Pick a sector/theme the user already believes may improve.
2. Add tickers that represent possible public-company vehicles for that theme.
3. Assign peer groups.
4. Enter SEC User-Agent in this format:

```text
Your Name your-email@example.com
```

Example:

```text
Sebastiaan Vriese savriese@gmail.com
```

5. Enter Finnhub API key.
6. Run **Run Full Pipeline** for one selected ticker, or **Run Full Pipeline For All Active** for the whole active watchlist.
7. Use **Sector Funnel** to find which names are flagged.
8. Use **Flag Review** to understand why the app flagged the ticker.
9. Work through **Data Check**, **Red Flag Check**, **Peer Gate**, and **Risk / Reward vs ETF**.
10. Use **Decision / Action** to decide Pass, Watchlist, Deep Dive, or Candidate Position.
11. If the decision is **Deep Dive**, leave the screener and start company research.
12. Use portfolio sizing only after the ticker becomes a true candidate position.

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
- Follow the screener-first sector workflow.
- Do not drift back to a generic business-school research checklist.
- Do not put manual exposure/leader/proof questions before the app's flag, numbers, peer, valuation, and risk checks.
- Every workflow step should help decide whether to continue, require proof, or pass for now.
- Keep raw/bulk data views secondary to the gate workflow.
- Keep readable screening views separate from raw data tables.
- Do not fake missing financial data.
- If data is partial, stale, unavailable, or currency-distorted, mark it clearly.
- Do not turn the app into broker integration, auto-trading, or automatic buy/sell recommendations.

## Still Needs To Be Done

### 1. Save gate notes per ticker

Needed:

- Add local database tables for gate notes.
- Save gate result per ticker and per gate.
- Save proof-needed notes.
- Save decision bucket.
- Save review trigger/date.
- Show gate status beside each ticker in the Sector Funnel.

### 2. Improve beginner usability

Needed:

- Add plain-English explanations to every gate.
- Add examples for each gate using real ticker examples.
- Add 'what a good answer means' and 'what a weak answer means.'
- Convert more raw table data into simple gate-level interpretation.
- Avoid jargon unless the app explains it.

### 3. Clean code structure

The app should have one clear window entry point and keep workflow UI code in a dedicated module once the layout is stable.

Needed:

- Keep only one real app window class.
- Move workflow UI customization out of `main.py` once stable.
- Remove unused visible-button logic if it is no longer used.
- Keep `main.py` small: import the app class and launch it.
- Confirm there are no unused wrapper files.

### 4. UI polish

Needed:

- Make workflow tabs readable at different window widths.
- Consider replacing top tabs with a left-side step navigator if the gate list gets cramped.
- Improve table column sizing presets.
- Save column widths.
- Improve loading/progress indicators during long full-pipeline runs.
- Improve error messages when API pulls fail.
- Make confirmation dialogs readable in dark mode without breaking launch.

### 5. Data quality and transparency

Needed:

- Per-field source confidence.
- Per-field source priority rules.
- Better distinction between reported, calculated, derived, estimated, and missing values.
- Better UI filtering for weak/incomplete data.
- More detailed data-quality summary by ticker.
- More explicit warnings for non-USD SEC units and ADR/foreign issuer issues.

### 6. Historical fundamentals

Partially added: `historical_fundamentals` is rebuilt from SEC annual companyfacts rows.

Still needed:

- More complete balance-sheet history where SEC coverage is partial.
- Historical balance-sheet trend calculations.
- Drill-downs showing which SEC concept supplied each historical value.
- Stronger restatement/duplicate annual fact handling.

### 7. Historical price data

Partially added: daily price candles are stored in `price_history`, and derived metrics are stored in `price_metrics`.

Still needed:

- Better adjusted-close support.
- Charting or sparkline UI.
- More configurable trend windows.
- Optional second fallback provider if Finnhub and Yahoo are unavailable or rate-limited.

### 8. Foreign issuer handling

Needed:

- More IFRS concept mappings.
- Better handling of non-USD reporting.
- Currency normalization or stronger currency warnings.
- ADR/share-count conversion awareness.
- Better disclosure notes for partial SBC, R&D, SG&A, and share-count coverage.

### 9. Workflow transparency

Partially added: the workflow now separates data checks, standalone red flags, and peer-relative comparisons.

Still needed:

- Version labels for workflow rules.
- Rule-by-rule rationale for red-flag checks.
- More detailed peer-relative drill-downs for valuation, quality, balance sheet, dilution, and FCF.

### 10. Peer group improvements

Needed:

- Better default peer-group templates.
- Peer-group editor.
- Automatic peer suggestions.
- More peer median and percentile ranks.
- Outlier detection.
- Option to exclude specific peers from comparison.

### 11. Privacy hardening

Needed:

- Startup check that warns if private local files are accidentally tracked by Git.
- Confirm `.db`, cache, log, build, and virtual environment files remain ignored.
- Optional local settings export/import.
- Better API-key masking.

### 12. Testing and release workflow

Needed:

- Unit tests for SEC concept mapping.
- Unit tests for Finnhub response mapping.
- Unit tests for normalization.
- Unit tests for readiness checks.
- Unit tests for peer comparison.
- Regression tests for foreign issuers such as TSM.
- Smoke test for launching the PySide app.
- Windows launch script.
- Optional packaged desktop build.
- Versioned releases.
- Stable Git tags for usable checkpoints.

## Do Not Add Yet

Do not add these until the data pipeline and workflow rules are more stable:

- Automated buy/sell recommendations.
- Broker integration.
- Auto-trading.
- Complex machine-learning models.
- Cloud sync.
- User accounts.

Portfolio sizing support is allowed only as a user-controlled planning aid, not as automatic allocation advice.

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
