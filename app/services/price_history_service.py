from __future__ import annotations

import datetime as dt
import math
from statistics import stdev
from typing import Optional

from app.db.database import get_connection


def to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_return(current, previous) -> Optional[float]:
    current = to_float(current)
    previous = to_float(previous)
    if current is None or previous in (None, 0):
        return None
    return (current / previous) - 1


def annualized_volatility(closes: list[float]) -> Optional[float]:
    if len(closes) < 3:
        return None
    returns = []
    for prev, curr in zip(closes, closes[1:]):
        if prev > 0 and curr > 0:
            returns.append(math.log(curr / prev))
    if len(returns) < 2:
        return None
    return stdev(returns) * math.sqrt(252)


def close_on_or_before(rows: list[dict], target: dt.date) -> Optional[float]:
    candidate = None
    for row in rows:
        if row["date"] <= target:
            candidate = row["close"]
        else:
            break
    return candidate


def momentum_flag(return_6m, return_1y) -> str:
    values = [x for x in (to_float(return_6m), to_float(return_1y)) if x is not None]
    if not values:
        return "GRAY - No Price Trend"
    if all(x > 0 for x in values):
        return "GREEN - Positive Momentum"
    if all(x < 0 for x in values):
        return "RED - Negative Momentum"
    return "YELLOW - Mixed Momentum"


def drawdown_flag(pct_from_high) -> str:
    value = to_float(pct_from_high)
    if value is None:
        return "GRAY - No 52W High"
    if value >= -0.10:
        return "GREEN - Near High"
    if value >= -0.25:
        return "YELLOW - Moderate Drawdown"
    return "RED - Deep Drawdown"


def volatility_flag(volatility_90d) -> str:
    value = to_float(volatility_90d)
    if value is None:
        return "GRAY - No Volatility"
    if value <= 0.35:
        return "GREEN - Lower Volatility"
    if value <= 0.65:
        return "YELLOW - Elevated Volatility"
    return "RED - High Volatility"


def recalculate_price_metrics_for_ticker(ticker: str) -> int:
    ticker = ticker.upper().strip()
    conn = get_connection()
    db_rows = conn.execute(
        """
        SELECT trade_date, high, low, close
        FROM price_history
        WHERE ticker = ?
          AND close IS NOT NULL
        ORDER BY trade_date ASC
        """,
        (ticker,),
    ).fetchall()

    rows = []
    for row in db_rows:
        close = to_float(row["close"])
        high = to_float(row["high"])
        low = to_float(row["low"])
        try:
            trade_date = dt.date.fromisoformat(str(row["trade_date"]))
        except ValueError:
            continue
        if close is not None:
            rows.append({"date": trade_date, "close": close, "high": high, "low": low})

    if not rows:
        conn.execute("DELETE FROM price_metrics WHERE ticker = ?", (ticker,))
        conn.commit()
        conn.close()
        return 0

    last = rows[-1]
    last_date = last["date"]
    last_close = last["close"]
    year_ago = last_date - dt.timedelta(days=365)
    rows_52w = [row for row in rows if row["date"] >= year_ago]
    high_52w = max((row["high"] for row in rows_52w if row["high"] is not None), default=None)
    low_52w = min((row["low"] for row in rows_52w if row["low"] is not None), default=None)

    close_1m = close_on_or_before(rows, last_date - dt.timedelta(days=30))
    close_3m = close_on_or_before(rows, last_date - dt.timedelta(days=91))
    close_6m = close_on_or_before(rows, last_date - dt.timedelta(days=182))
    close_1y = close_on_or_before(rows, last_date - dt.timedelta(days=365))
    close_3y = close_on_or_before(rows, last_date - dt.timedelta(days=365 * 3))

    closes = [row["close"] for row in rows]
    vol_30d = annualized_volatility(closes[-31:])
    vol_90d = annualized_volatility(closes[-91:])
    pct_from_high = safe_return(last_close, high_52w)
    pct_above_low = safe_return(last_close, low_52w)
    ret_6m = safe_return(last_close, close_6m)
    ret_1y = safe_return(last_close, close_1y)

    values = {
        "ticker": ticker,
        "lookback_days": len(rows),
        "last_trade_date": last_date.isoformat(),
        "last_close": last_close,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "pct_from_52w_high": pct_from_high,
        "pct_above_52w_low": pct_above_low,
        "return_1m": safe_return(last_close, close_1m),
        "return_3m": safe_return(last_close, close_3m),
        "return_6m": ret_6m,
        "return_1y": ret_1y,
        "return_3y": safe_return(last_close, close_3y),
        "volatility_30d": vol_30d,
        "volatility_90d": vol_90d,
        "momentum_flag": momentum_flag(ret_6m, ret_1y),
        "drawdown_flag": drawdown_flag(pct_from_high),
        "volatility_flag": volatility_flag(vol_90d),
        "source_status": "FINNHUB DAILY CANDLES",
    }

    conn.execute(
        """
        INSERT INTO price_metrics (
            ticker, lookback_days, last_trade_date, last_close,
            high_52w, low_52w, pct_from_52w_high, pct_above_52w_low,
            return_1m, return_3m, return_6m, return_1y, return_3y,
            volatility_30d, volatility_90d,
            momentum_flag, drawdown_flag, volatility_flag, source_status, updated_at
        )
        VALUES (
            :ticker, :lookback_days, :last_trade_date, :last_close,
            :high_52w, :low_52w, :pct_from_52w_high, :pct_above_52w_low,
            :return_1m, :return_3m, :return_6m, :return_1y, :return_3y,
            :volatility_30d, :volatility_90d,
            :momentum_flag, :drawdown_flag, :volatility_flag, :source_status, CURRENT_TIMESTAMP
        )
        ON CONFLICT(ticker) DO UPDATE SET
            lookback_days = excluded.lookback_days,
            last_trade_date = excluded.last_trade_date,
            last_close = excluded.last_close,
            high_52w = excluded.high_52w,
            low_52w = excluded.low_52w,
            pct_from_52w_high = excluded.pct_from_52w_high,
            pct_above_52w_low = excluded.pct_above_52w_low,
            return_1m = excluded.return_1m,
            return_3m = excluded.return_3m,
            return_6m = excluded.return_6m,
            return_1y = excluded.return_1y,
            return_3y = excluded.return_3y,
            volatility_30d = excluded.volatility_30d,
            volatility_90d = excluded.volatility_90d,
            momentum_flag = excluded.momentum_flag,
            drawdown_flag = excluded.drawdown_flag,
            volatility_flag = excluded.volatility_flag,
            source_status = excluded.source_status,
            updated_at = CURRENT_TIMESTAMP
        """,
        values,
    )
    conn.commit()
    conn.close()
    return 1


def recalculate_all_price_metrics() -> int:
    conn = get_connection()
    tickers = [r["ticker"] for r in conn.execute("SELECT DISTINCT ticker FROM price_history ORDER BY ticker").fetchall()]
    conn.close()
    count = 0
    for ticker in tickers:
        count += recalculate_price_metrics_for_ticker(ticker)
    return count
