from __future__ import annotations

import datetime as dt
import time
from typing import Any

import requests

from app.services.finnhub_service import refresh_finnhub_price_history

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
}


def yahoo_symbol(ticker: str) -> str:
    return ticker.upper().strip().replace(".", "-")


def parse_yahoo_chart_rows(ticker: str, data: dict[str, Any]) -> list[dict]:
    chart = data.get("chart") if isinstance(data, dict) else None
    if not isinstance(chart, dict):
        raise RuntimeError("Yahoo chart response missing chart object")

    error = chart.get("error")
    if error:
        description = error.get("description") if isinstance(error, dict) else str(error)
        raise RuntimeError(f"Yahoo chart error: {description}")

    results = chart.get("result") or []
    if not results:
        return []

    result = results[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    quotes = indicators.get("quote") or []
    quote = quotes[0] if quotes else {}
    adjclose_rows = indicators.get("adjclose") or []
    adjclose = (adjclose_rows[0] or {}).get("adjclose") if adjclose_rows else []

    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []

    rows = []
    ticker = ticker.upper().strip()
    for idx, stamp in enumerate(timestamps):
        try:
            trade_date = dt.datetime.fromtimestamp(int(stamp), tz=dt.timezone.utc).date().isoformat()
        except Exception:
            continue

        close = closes[idx] if idx < len(closes) else None
        if close is None:
            continue

        rows.append({
            "ticker": ticker,
            "trade_date": trade_date,
            "open": opens[idx] if idx < len(opens) else None,
            "high": highs[idx] if idx < len(highs) else None,
            "low": lows[idx] if idx < len(lows) else None,
            "close": close,
            "adjusted_close": adjclose[idx] if idx < len(adjclose) else close,
            "volume": volumes[idx] if idx < len(volumes) else None,
            "source": "YAHOO_CHART",
        })
    return rows


def refresh_yahoo_price_history(ticker: str, lookback_years: int = 3) -> list[dict]:
    ticker = ticker.upper().strip()
    lookback_years = max(1, min(int(lookback_years or 3), 10))
    period2 = int(time.time())
    period1 = period2 - (lookback_years * 365 * 24 * 60 * 60)
    response = requests.get(
        YAHOO_CHART_URL.format(symbol=yahoo_symbol(ticker)),
        params={
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        },
        headers=REQUEST_HEADERS,
        timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Yahoo chart HTTP {response.status_code}: {response.text[:500]}")
    return parse_yahoo_chart_rows(ticker, response.json())


def refresh_price_history_rows(ticker: str, finnhub_key: str = "", lookback_years: int = 3) -> tuple[list[dict], str, str]:
    finnhub_error = ""
    if finnhub_key:
        try:
            rows = refresh_finnhub_price_history(ticker, finnhub_key, lookback_years=lookback_years)
            if rows:
                return rows, "FINNHUB", ""
            finnhub_error = "Finnhub returned no candle rows"
        except Exception as exc:
            finnhub_error = str(exc)

    yahoo_rows = refresh_yahoo_price_history(ticker, lookback_years=lookback_years)
    if yahoo_rows:
        note = "Finnhub candle API unavailable; used Yahoo chart fallback." if finnhub_error else ""
        return yahoo_rows, "YAHOO_CHART", note

    if finnhub_error:
        return [], "", f"Finnhub: {finnhub_error}; Yahoo returned no chart rows."
    return [], "", "Yahoo returned no chart rows."
