from __future__ import annotations

import datetime as dt

from app.db.database import get_connection
from app.services.watchlist_service import fmt_millions, fmt_percent, fmt_price, fmt_ratio, safe_float


SEC_STALE_DAYS = 460
FINNHUB_STALE_DAYS = 10
PRICE_STALE_DAYS = 10


def parse_timestamp(value: str | None):
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return parsed


def days_old(value: str | None):
    parsed = parse_timestamp(value)
    if parsed is None:
        return None
    now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
    return max(0, (now - parsed).days)


def freshness_label(value: str | None, stale_days: int) -> tuple[str, bool]:
    age = days_old(value)
    if age is None:
        return "Unknown", True
    if age > stale_days:
        return f"{age} days old", True
    return f"{age} days old", False


def first_present(*values):
    for value in values:
        if value is not None:
            return value
    return None


def status_for_value(value, freshness: str, stale: bool) -> str:
    if value is None:
        return "GRAY - Missing"
    if stale:
        return "YELLOW - Stale"
    return "GREEN - Complete"


def partial_status(present_count: int, total_count: int, stale: bool = False) -> str:
    if present_count == 0:
        return "GRAY - Missing"
    if present_count < total_count:
        return "YELLOW - Partial"
    if stale:
        return "YELLOW - Stale"
    return "GREEN - Complete"


def format_value(field: str, value) -> str:
    if value is None:
        return ""
    if field in {"Price"}:
        return fmt_price(value)
    if field in {"Current Ratio"}:
        return fmt_ratio(value)
    if field in {"Dilution", "SBC / R&D / SG&A"}:
        return str(value)
    return fmt_millions(value)


def quality_row(ticker: str, field: str, status: str, value: str, source: str, freshness: str, action: str, notes: str) -> dict:
    return {
        "Ticker": ticker,
        "Field": field,
        "Quality Status": status,
        "Value": value,
        "Source": source,
        "Freshness": freshness,
        "Suggested Action": action,
        "Notes": notes,
    }


def status_category(status: str) -> str:
    return (status or "").split(" ", 1)[0].upper()


def status_points(status: str) -> int:
    category = status_category(status)
    if category == "GREEN":
        return 100
    if category in {"YELLOW", "PURPLE"}:
        return 65
    if category == "GRAY":
        return 25
    if category == "RED":
        return 0
    return 40


def quality_flag(score: int, missing_count: int, warning_count: int) -> str:
    if missing_count >= 5:
        return "RED - Data Weak"
    if missing_count > 0:
        return "YELLOW - Missing Fields"
    if warning_count > 0:
        return "YELLOW - Review Data"
    if score >= 85:
        return "GREEN - Data Strong"
    return "YELLOW - Data Usable"


def latest_created_at(conn, ticker: str, source: str | None = None, table: str = "api_cache") -> str | None:
    if table == "price_history":
        row = conn.execute("SELECT MAX(updated_at) AS ts FROM price_history WHERE ticker = ?", (ticker,)).fetchone()
        return row["ts"] if row else None
    if table == "historical_fundamentals":
        row = conn.execute("SELECT MAX(updated_at) AS ts FROM historical_fundamentals WHERE ticker = ?", (ticker,)).fetchone()
        return row["ts"] if row else None
    if source:
        row = conn.execute(
            "SELECT MAX(created_at) AS ts FROM api_cache WHERE ticker = ? AND source = ?",
            (ticker, source),
        ).fetchone()
    else:
        row = conn.execute("SELECT MAX(created_at) AS ts FROM api_cache WHERE ticker = ?", (ticker,)).fetchone()
    return row["ts"] if row else None


def price_metric_count(conn, ticker: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS count FROM price_metrics WHERE ticker = ?", (ticker,)).fetchone()
    return int(row["count"] or 0) if row else 0


def historical_year_count(conn, ticker: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS count FROM historical_fundamentals WHERE ticker = ?", (ticker,)).fetchone()
    return int(row["count"] or 0) if row else 0


def non_usd_sec_units(conn, ticker: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT unit
        FROM api_cache
        WHERE ticker = ?
          AND source = 'SEC EDGAR'
          AND unit IS NOT NULL
          AND unit <> ''
          AND unit NOT IN ('USD', 'USD/shares', 'shares', 'pure')
        ORDER BY unit
        """,
        (ticker,),
    ).fetchall()
    return [row["unit"] for row in rows]


def list_data_quality(ticker: str | None = None) -> list[dict]:
    conn = get_connection()
    params = []
    ticker_clause = ""
    if ticker:
        ticker_clause = "WHERE md.ticker = ?"
        params.append(ticker.upper().strip())

    rows = conn.execute(
        f"""
        SELECT
            md.*,
            mr.readiness,
            mr.missing_weak_areas
        FROM market_data md
        LEFT JOIN model_readiness mr ON mr.ticker = md.ticker
        {ticker_clause}
        ORDER BY md.ticker
        """,
        params,
    ).fetchall()

    out = []
    for row in rows:
        ticker_value = row["ticker"]
        sec_ts = latest_created_at(conn, ticker_value, "SEC EDGAR")
        finnhub_ts = latest_created_at(conn, ticker_value, "FINNHUB")
        price_ts = latest_created_at(conn, ticker_value, table="price_history")
        history_ts = latest_created_at(conn, ticker_value, table="historical_fundamentals")
        sec_freshness, sec_stale = freshness_label(sec_ts, SEC_STALE_DAYS)
        finnhub_freshness, finnhub_stale = freshness_label(finnhub_ts, FINNHUB_STALE_DAYS)
        price_freshness, price_stale = freshness_label(price_ts, PRICE_STALE_DAYS)
        history_freshness, history_stale = freshness_label(history_ts, SEC_STALE_DAYS)

        fields = [
            ("Price", row["price_per_share"], "Finnhub quote / Price history", finnhub_freshness, finnhub_stale, "Refresh Finnhub or price history"),
            ("Market Cap", row["market_cap_raw"], "Finnhub metric / derived", finnhub_freshness, finnhub_stale, "Refresh Finnhub metrics"),
            ("Shares", first_present(row["shares_out_raw"], row["diluted_shares_raw"]), "Finnhub / SEC", finnhub_freshness, finnhub_stale, "Refresh Finnhub and SEC"),
            ("Revenue", row["revenue_raw"], "SEC annual facts / Finnhub fallback", sec_freshness, sec_stale, "Refresh SEC data"),
            ("Gross Profit", row["gross_profit_raw"], "SEC annual facts / derived fallback", sec_freshness, sec_stale, "Refresh SEC data; inspect concept mapping"),
            ("EBITDA", row["ebitda_raw"], "Finnhub / derived from SEC", finnhub_freshness, finnhub_stale, "Refresh Finnhub and SEC"),
            ("FCF", row["fcf_raw"], "Derived from SEC OCF and capex", sec_freshness, sec_stale, "Refresh SEC data; inspect OCF/capex"),
            ("Cash", row["cash_raw"], "SEC balance sheet", sec_freshness, sec_stale, "Refresh SEC data"),
            ("Debt", row["debt_raw"], "SEC balance sheet", sec_freshness, sec_stale, "Refresh SEC data"),
            ("Current Ratio", row["current_ratio"], "Derived from SEC current assets/liabilities", sec_freshness, sec_stale, "Refresh SEC data"),
        ]

        for field, value, source, freshness, stale, action in fields:
            out.append(quality_row(
                ticker_value,
                field,
                status_for_value(value, freshness, stale),
                format_value(field, value),
                source,
                freshness,
                action if value is None or stale else "No action needed",
                row["missing_weak_areas"] or "",
            ))

        dilution_values = [row["dilution_1y"], row["dilution_3y"]]
        dilution_present = sum(1 for value in dilution_values if value is not None)
        dilution_value = f"1Y {fmt_percent(row['dilution_1y'])}; 3Y {fmt_percent(row['dilution_3y'])}"
        out.append(quality_row(
            ticker_value,
            "Dilution",
            partial_status(dilution_present, 2, sec_stale),
            dilution_value,
            "SEC annual share history",
            sec_freshness,
            "Refresh SEC data; inspect share concepts" if dilution_present < 2 or sec_stale else "No action needed",
            row["missing_weak_areas"] or "",
        ))

        expense_values = [row["sbc_raw"], row["rd_raw"], row["sga_raw"]]
        expense_present = sum(1 for value in expense_values if value is not None)
        expense_value = f"SBC {fmt_millions(row['sbc_raw'])}; R&D {fmt_millions(row['rd_raw'])}; SG&A {fmt_millions(row['sga_raw'])}"
        out.append(quality_row(
            ticker_value,
            "SBC / R&D / SG&A",
            partial_status(expense_present, 3, sec_stale),
            expense_value,
            "SEC expense concepts",
            sec_freshness,
            "Inspect SEC concepts; foreign issuers may be partial" if expense_present < 3 or sec_stale else "No action needed",
            row["missing_weak_areas"] or "",
        ))

        price_count = price_metric_count(conn, ticker_value)
        out.append(quality_row(
            ticker_value,
            "Price Trends",
            partial_status(price_count, 1, price_stale),
            f"{price_count} trend row(s)",
            "Finnhub daily candles",
            price_freshness,
            "Refresh price history" if price_count == 0 or price_stale else "No action needed",
            "Momentum/drawdown/volatility depend on stored daily candles.",
        ))

        history_count = historical_year_count(conn, ticker_value)
        out.append(quality_row(
            ticker_value,
            "Historical Fundamentals",
            "GREEN - Complete" if history_count >= 3 and not history_stale else "YELLOW - Partial" if history_count > 0 else "GRAY - Missing",
            f"{history_count} year(s)",
            "SEC annual companyfacts history",
            history_freshness,
            "Rebuild SEC history" if history_count == 0 or history_stale else "No action needed",
            "Three or more annual rows gives the screener enough trend context for a first pass.",
        ))

        foreign_units = non_usd_sec_units(conn, ticker_value)
        if foreign_units:
            out.append(quality_row(
                ticker_value,
                "Currency / Foreign Issuer",
                "YELLOW - Currency Warning",
                ", ".join(foreign_units),
                "SEC companyfacts units",
                sec_freshness,
                "Treat valuation multiples carefully until currency normalization is added",
                "SEC fundamentals may be reported in a non-USD currency while market cap/EV are usually USD.",
            ))

    conn.close()
    status_order = {"GRAY": 0, "RED": 1, "YELLOW": 2, "PURPLE": 3, "GREEN": 4}
    return sorted(out, key=lambda item: (item["Ticker"], status_order.get(item["Quality Status"].split(" ", 1)[0], 9), item["Field"]))


def list_data_quality_summary(ticker: str | None = None) -> list[dict]:
    detail_rows = list_data_quality(ticker)
    grouped: dict[str, list[dict]] = {}
    for row in detail_rows:
        grouped.setdefault(row["Ticker"], []).append(row)

    out = []
    for ticker_value, rows in grouped.items():
        total = len(rows)
        complete = sum(1 for row in rows if status_category(row["Quality Status"]) == "GREEN")
        missing = sum(1 for row in rows if status_category(row["Quality Status"]) == "GRAY")
        red = sum(1 for row in rows if status_category(row["Quality Status"]) == "RED")
        warnings = sum(1 for row in rows if status_category(row["Quality Status"]) in {"YELLOW", "PURPLE"})
        currency_warnings = sum(1 for row in rows if row["Field"] == "Currency / Foreign Issuer")
        score = round(sum(status_points(row["Quality Status"]) for row in rows) / total) if total else 0
        weak_rows = [row for row in rows if status_category(row["Quality Status"]) != "GREEN"]
        worst_fields = ", ".join(row["Field"] for row in weak_rows[:6]) if weak_rows else "None"
        next_action = "No action needed"
        for row in weak_rows:
            action = row.get("Suggested Action") or ""
            if action and action != "No action needed":
                next_action = action
                break
        flag = quality_flag(score, missing + red, warnings)
        out.append({
            "Ticker": ticker_value,
            "Data Quality Score": str(score),
            "Data Quality Flag": flag,
            "Complete Fields": str(complete),
            "Warnings": str(warnings),
            "Missing / Red": str(missing + red),
            "Currency Warnings": str(currency_warnings),
            "Suggested Next Step": next_action,
            "Weakest Fields": worst_fields,
        })

    return sorted(out, key=lambda row: (int(row["Data Quality Score"]), row["Ticker"]))
