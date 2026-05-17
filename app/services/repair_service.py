from __future__ import annotations

from dataclasses import dataclass

from app.db.database import get_connection, insert_price_history_rows, list_tickers
from app.services.data_quality_service import list_data_quality_summary
from app.services.historical_data_service import rebuild_historical_fundamentals_for_ticker
from app.services.market_data_service import normalize_market_data_for_ticker
from app.services.price_data_service import refresh_price_history_rows
from app.services.price_history_service import recalculate_price_metrics_for_ticker
from app.services.readiness_service import calculate_model_readiness_for_ticker


@dataclass
class RepairResult:
    ticker: str
    history_years: int = 0
    price_rows: int = 0
    price_source: str = ""
    price_note: str = ""
    normalized: bool = False
    readiness: bool = False
    warning: str = ""


def active_tickers() -> list[str]:
    return [row["ticker"] for row in list_tickers() if (row["status"] or "active") == "active"]


def tickers_with_any_data() -> set[str]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT ticker FROM api_cache
        UNION
        SELECT ticker FROM market_data
        UNION
        SELECT ticker FROM price_history
        UNION
        SELECT ticker FROM price_metrics
        """
    ).fetchall()
    conn.close()
    return {row["ticker"] for row in rows}


def tickers_missing_price_metrics() -> set[str]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.ticker
        FROM tickers t
        LEFT JOIN price_metrics pm ON pm.ticker = t.ticker
        WHERE COALESCE(t.status, 'active') = 'active'
          AND pm.ticker IS NULL
        """
    ).fetchall()
    conn.close()
    return {row["ticker"] for row in rows}


def price_history_count(ticker: str) -> int:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS count FROM price_history WHERE ticker = ?", (ticker,)).fetchone()
    conn.close()
    return int(row["count"] or 0) if row else 0


def tickers_missing_historical_fundamentals() -> set[str]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.ticker
        FROM tickers t
        LEFT JOIN historical_fundamentals hf ON hf.ticker = t.ticker
        WHERE COALESCE(t.status, 'active') = 'active'
        GROUP BY t.ticker
        HAVING COUNT(hf.fiscal_year) < 3
        """
    ).fetchall()
    conn.close()
    return {row["ticker"] for row in rows}


def repair_ticker_missing_data(ticker: str, finnhub_key: str = "", lookback_years: int = 3) -> RepairResult:
    ticker = ticker.upper().strip()
    result = RepairResult(ticker=ticker)
    warnings = []

    try:
        result.history_years = rebuild_historical_fundamentals_for_ticker(ticker)
    except Exception as exc:
        warnings.append(f"history: {exc}")

    should_fetch_price = bool(finnhub_key) or price_history_count(ticker) == 0
    if should_fetch_price:
        try:
            price_rows, source, note = refresh_price_history_rows(ticker, finnhub_key, lookback_years=lookback_years)
            result.price_rows = insert_price_history_rows(price_rows)
            result.price_source = source
            result.price_note = note
            recalculate_price_metrics_for_ticker(ticker)
        except Exception as exc:
            warnings.append(f"price: {exc}")
    else:
        try:
            recalculate_price_metrics_for_ticker(ticker)
        except Exception as exc:
            warnings.append(f"price metrics: {exc}")

    try:
        normalize_market_data_for_ticker(ticker)
        result.normalized = True
    except Exception as exc:
        warnings.append(f"normalize: {exc}")

    try:
        calculate_model_readiness_for_ticker(ticker)
        result.readiness = True
    except Exception as exc:
        warnings.append(f"readiness: {exc}")

    result.warning = "; ".join(warnings)
    return result


def repair_all_missing_data(finnhub_key: str = "", lookback_years: int = 3, only_missing: bool = True) -> list[RepairResult]:
    if only_missing:
        targets = tickers_missing_historical_fundamentals() | tickers_missing_price_metrics()
        targets |= {row["Ticker"] for row in list_data_quality_summary() if not str(row.get("Data Quality Flag", "")).startswith("GREEN")}
    else:
        targets = set(active_tickers())

    active = set(active_tickers())
    if only_missing:
        targets &= tickers_with_any_data()
    ordered_targets = [ticker for ticker in sorted(targets & active)]

    return [
        repair_ticker_missing_data(ticker, finnhub_key=finnhub_key, lookback_years=lookback_years)
        for ticker in ordered_targets
    ]
