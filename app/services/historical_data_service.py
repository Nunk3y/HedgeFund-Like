from __future__ import annotations

from typing import Optional

from app.db.database import get_connection


SEC_HISTORY_FIELD_TO_COL = {
    "revenue": "revenue_raw",
    "gross_profit": "gross_profit_raw",
    "operating_income": "operating_income_raw",
    "net_income": "net_income_raw",
    "operating_cash_flow": "operating_cash_flow_raw",
    "capital_expenditures": "capex_raw",
    "cash_and_equivalents": "cash_raw",
    "current_assets": "current_assets_raw",
    "current_liabilities": "current_liabilities_raw",
    "total_equity": "equity_raw",
}

BASE_VALUES = {
    "revenue_raw": None,
    "gross_profit_raw": None,
    "operating_income_raw": None,
    "net_income_raw": None,
    "operating_cash_flow_raw": None,
    "capex_raw": None,
    "fcf_raw": None,
    "cash_raw": None,
    "current_assets_raw": None,
    "current_liabilities_raw": None,
    "current_ratio": None,
    "debt_raw": None,
    "equity_raw": None,
    "shares_raw": None,
    "dilution_yoy": None,
    "revenue_growth_yoy": None,
    "gross_profit_growth_yoy": None,
    "operating_income_growth_yoy": None,
    "net_income_growth_yoy": None,
    "fcf_growth_yoy": None,
    "cash_growth_yoy": None,
    "debt_growth_yoy": None,
    "shares_growth_yoy": None,
    "gross_margin": None,
    "operating_margin": None,
    "fcf_margin": None,
}


def to_float(value) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() == "null":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def safe_ratio(numerator, denominator) -> Optional[float]:
    numerator = to_float(numerator)
    denominator = to_float(denominator)
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def growth_rate(current, previous) -> Optional[float]:
    current = to_float(current)
    previous = to_float(previous)
    if current is None or previous in (None, 0):
        return None
    return (current - previous) / abs(previous)


def annual_field_name(raw_field: str) -> str:
    raw_field = raw_field or ""
    return raw_field[:-8] if raw_field.endswith("_history") else raw_field


def blank_year(ticker: str, fiscal_year: int) -> dict:
    row = {"ticker": ticker, "fiscal_year": fiscal_year, "period": "", "filed": "", "form": ""}
    row.update(BASE_VALUES)
    row["source_status"] = "SEC EDGAR ANNUAL HISTORY"
    row["source_notes"] = ""
    return row


def maybe_update_metadata(year_row: dict, cache_row) -> None:
    for key, db_col in [("period", "period"), ("filed", "filed"), ("form", "form")]:
        value = cache_row[db_col] if db_col in cache_row.keys() else ""
        if value and not year_row.get(key):
            year_row[key] = value


def add_source_note(year_row: dict, field: str, cache_row) -> None:
    concept = cache_row["sec_concept"] if "sec_concept" in cache_row.keys() else ""
    unit = cache_row["unit"] if "unit" in cache_row.keys() else ""
    note = f"{field}:{concept or 'unknown'}:{unit or 'unknown'}"
    current = [x for x in year_row.get("source_notes", "").split("; ") if x]
    if note not in current:
        current.append(note)
    year_row["source_notes"] = "; ".join(current)[:2000]


def rebuild_historical_fundamentals_for_ticker(ticker: str) -> int:
    ticker = ticker.upper().strip()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            ticker, endpoint, raw_field, raw_value, period, fiscal_year, status,
            sec_concept, unit, form, filed
        FROM api_cache
        WHERE ticker = ?
          AND source = 'SEC EDGAR'
          AND endpoint = 'companyfacts_annual_history'
          AND status = 'OK'
          AND fiscal_year IS NOT NULL
          AND fiscal_year <> ''
        ORDER BY fiscal_year ASC, id ASC
        """,
        (ticker,),
    ).fetchall()

    by_year: dict[int, dict] = {}
    debt_current: dict[int, float] = {}
    debt_noncurrent: dict[int, float] = {}

    for cache_row in rows:
        fiscal_year = to_int(cache_row["fiscal_year"])
        if fiscal_year is None:
            continue
        value = to_float(cache_row["raw_value"])
        if value is None:
            continue

        year_row = by_year.setdefault(fiscal_year, blank_year(ticker, fiscal_year))
        maybe_update_metadata(year_row, cache_row)
        field = annual_field_name(cache_row["raw_field"])

        if field in SEC_HISTORY_FIELD_TO_COL:
            year_row[SEC_HISTORY_FIELD_TO_COL[field]] = value
            add_source_note(year_row, field, cache_row)
        elif field == "debt_current":
            debt_current[fiscal_year] = value
            add_source_note(year_row, field, cache_row)
        elif field == "debt_noncurrent":
            debt_noncurrent[fiscal_year] = value
            add_source_note(year_row, field, cache_row)
        elif field == "shares_diluted":
            year_row["shares_raw"] = value
            add_source_note(year_row, field, cache_row)
        elif field == "shares_basic" and year_row.get("shares_raw") is None:
            year_row["shares_raw"] = value
            add_source_note(year_row, field, cache_row)

    for fiscal_year, year_row in by_year.items():
        debt_parts = [debt_current.get(fiscal_year), debt_noncurrent.get(fiscal_year)]
        debt_values = [x for x in debt_parts if x is not None]
        if debt_values:
            year_row["debt_raw"] = sum(debt_values)

        ocf = year_row.get("operating_cash_flow_raw")
        capex = year_row.get("capex_raw")
        if ocf is not None and capex is not None:
            year_row["fcf_raw"] = ocf + capex if capex < 0 else ocf - capex

        revenue = year_row.get("revenue_raw")
        year_row["gross_margin"] = safe_ratio(year_row.get("gross_profit_raw"), revenue)
        year_row["operating_margin"] = safe_ratio(year_row.get("operating_income_raw"), revenue)
        year_row["fcf_margin"] = safe_ratio(year_row.get("fcf_raw"), revenue)
        year_row["current_ratio"] = safe_ratio(year_row.get("current_assets_raw"), year_row.get("current_liabilities_raw"))

    previous = None
    for fiscal_year in sorted(by_year):
        year_row = by_year[fiscal_year]
        if previous:
            year_row["revenue_growth_yoy"] = growth_rate(year_row.get("revenue_raw"), previous.get("revenue_raw"))
            year_row["gross_profit_growth_yoy"] = growth_rate(year_row.get("gross_profit_raw"), previous.get("gross_profit_raw"))
            year_row["operating_income_growth_yoy"] = growth_rate(year_row.get("operating_income_raw"), previous.get("operating_income_raw"))
            year_row["net_income_growth_yoy"] = growth_rate(year_row.get("net_income_raw"), previous.get("net_income_raw"))
            year_row["fcf_growth_yoy"] = growth_rate(year_row.get("fcf_raw"), previous.get("fcf_raw"))
            year_row["cash_growth_yoy"] = growth_rate(year_row.get("cash_raw"), previous.get("cash_raw"))
            year_row["debt_growth_yoy"] = growth_rate(year_row.get("debt_raw"), previous.get("debt_raw"))
            year_row["shares_growth_yoy"] = growth_rate(year_row.get("shares_raw"), previous.get("shares_raw"))
            year_row["dilution_yoy"] = year_row["shares_growth_yoy"]
        previous = year_row

    conn.execute("DELETE FROM historical_fundamentals WHERE ticker = ?", (ticker,))
    if by_year:
        conn.executemany(
            """
            INSERT INTO historical_fundamentals (
                ticker, fiscal_year, period, filed, form,
                revenue_raw, gross_profit_raw, operating_income_raw, net_income_raw,
                operating_cash_flow_raw, capex_raw, fcf_raw,
                cash_raw, current_assets_raw, current_liabilities_raw, current_ratio,
                debt_raw, equity_raw, shares_raw, dilution_yoy,
                revenue_growth_yoy, gross_profit_growth_yoy, operating_income_growth_yoy,
                net_income_growth_yoy, fcf_growth_yoy, cash_growth_yoy, debt_growth_yoy,
                shares_growth_yoy, gross_margin, operating_margin, fcf_margin,
                source_status, source_notes, updated_at
            )
            VALUES (
                :ticker, :fiscal_year, :period, :filed, :form,
                :revenue_raw, :gross_profit_raw, :operating_income_raw, :net_income_raw,
                :operating_cash_flow_raw, :capex_raw, :fcf_raw,
                :cash_raw, :current_assets_raw, :current_liabilities_raw, :current_ratio,
                :debt_raw, :equity_raw, :shares_raw, :dilution_yoy,
                :revenue_growth_yoy, :gross_profit_growth_yoy, :operating_income_growth_yoy,
                :net_income_growth_yoy, :fcf_growth_yoy, :cash_growth_yoy, :debt_growth_yoy,
                :shares_growth_yoy, :gross_margin, :operating_margin, :fcf_margin,
                :source_status, :source_notes, CURRENT_TIMESTAMP
            )
            """,
            [by_year[y] for y in sorted(by_year, reverse=True)],
        )
    conn.commit()
    conn.close()
    return len(by_year)


def rebuild_all_historical_fundamentals() -> int:
    conn = get_connection()
    tickers = [r["ticker"] for r in conn.execute("SELECT DISTINCT ticker FROM api_cache WHERE source = 'SEC EDGAR' ORDER BY ticker").fetchall()]
    conn.close()
    count = 0
    for ticker in tickers:
        count += rebuild_historical_fundamentals_for_ticker(ticker)
    return count
