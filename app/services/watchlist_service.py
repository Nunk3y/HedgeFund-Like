from __future__ import annotations

from app.db.database import get_connection
from app.services.flag_service import (
    flag_data_confidence,
    flag_balance_sheet,
    flag_quality,
    flag_valuation,
    flag_dilution,
)


def fmt_billions(value) -> str:
    if value is None:
        return ""
    try:
        return f"${float(value) / 1_000_000_000:,.3f}B"
    except Exception:
        return ""


def fmt_millions(value) -> str:
    if value is None:
        return ""
    try:
        return f"${float(value) / 1_000_000:,.3f}M"
    except Exception:
        return ""


def fmt_shares_millions(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) / 1_000_000:,.3f}M"
    except Exception:
        return ""


def fmt_price(value) -> str:
    if value is None:
        return ""
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return ""


def fmt_ratio(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):,.2f}x"
    except Exception:
        return ""


def fmt_ev_fcf(value, fcf) -> str:
    if fcf is None:
        return "MISSING FCF"
    try:
        fcf = float(fcf)
    except Exception:
        return "MISSING FCF"
    if fcf < 0:
        return "NEG FCF"
    if fcf == 0:
        return "ZERO FCF"
    return fmt_ratio(value)


def fmt_percent(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:,.2f}%"
    except Exception:
        return ""


def safe_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_multiple(numerator, denominator):
    numerator = safe_float(numerator)
    denominator = safe_float(denominator)
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def score_data(readiness: str | None, source_status: str | None) -> int:
    readiness = readiness or ""
    source_status = source_status or ""
    if "MODEL READY" in readiness or "READY FOR PEER COMPARISON" in readiness or "READY FOR DEEP-DIVE SCREENING" in readiness:
        return 100
    if "PRE-REVENUE" in readiness:
        return 55
    if "PARTIAL" in readiness:
        return 70
    if source_status:
        return 45
    return 20


def flag_level(flag: str) -> str:
    flag = str(flag or "").upper()
    if flag.startswith("RED"):
        return "red"
    if flag.startswith("YELLOW") or flag.startswith("PURPLE"):
        return "watch"
    if flag.startswith("GRAY"):
        return "data"
    if flag.startswith("GREEN"):
        return "clear"
    return "neutral"


def summarize_red_flags(
    data_flag: str,
    quality_flag: str,
    valuation_flag: str,
    balance_flag: str,
    dilution_flag: str,
    peer_group: str,
) -> tuple[str, str, str, str]:
    red_flags: list[str] = []
    watch_items: list[str] = []

    if flag_level(data_flag) == "data":
        red_flags.append(data_flag)
    if not peer_group:
        red_flags.append("GRAY — No Peer Group")

    for flag in [quality_flag, valuation_flag, balance_flag, dilution_flag]:
        level = flag_level(flag)
        if level == "red":
            red_flags.append(flag)
        elif level == "watch":
            watch_items.append(flag)

    if any(str(flag).startswith("GRAY") for flag in red_flags):
        result = "GRAY — Fix Data First"
        action = "Fix data or peer group before comparing this ticker."
    elif red_flags:
        result = "RED — Red Flag"
        action = "Stop unless there is a specific reason this red flag is acceptable."
    elif watch_items:
        result = "YELLOW — Needs Context"
        action = "Review watch items, then continue to Peer Gate if they are acceptable."
    else:
        result = "GREEN — Ready For Peer Gate"
        action = "Move to Peer Gate and compare against alternatives."

    return (
        result,
        "; ".join(red_flags) if red_flags else "None flagged",
        "; ".join(watch_items) if watch_items else "None flagged",
        action,
    )


def list_master_watchlist():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            md.*,
            mr.readiness,
            mr.next_action,
            mr.missing_weak_areas,
            mr.core_data_score,
            pm.last_trade_date AS price_last_trade_date,
            pm.return_1m AS price_return_1m,
            pm.return_3m AS price_return_3m,
            pm.return_6m AS price_return_6m,
            pm.return_1y AS price_return_1y,
            pm.return_3y AS price_return_3y,
            pm.pct_from_52w_high AS price_pct_from_52w_high,
            pm.volatility_90d AS price_volatility_90d,
            pm.momentum_flag AS price_momentum_flag,
            pm.drawdown_flag AS price_drawdown_flag,
            pm.volatility_flag AS price_volatility_flag
        FROM market_data md
        LEFT JOIN model_readiness mr ON mr.ticker = md.ticker
        LEFT JOIN price_metrics pm ON pm.ticker = md.ticker
        ORDER BY md.ticker
        """
    ).fetchall()
    conn.close()

    out = []
    for r in rows:
        ev_rev = safe_multiple(r["enterprise_value_raw"], r["revenue_raw"])
        fcf = safe_float(r["fcf_raw"])
        ev_fcf = safe_multiple(r["enterprise_value_raw"], fcf) if fcf and fcf > 0 else None
        ps = safe_multiple(r["market_cap_raw"], r["revenue_raw"])
        cash_runway = None
        if r["cash_raw"] is not None and fcf is not None and fcf < 0:
            cash_runway = abs(float(r["cash_raw"]) / fcf)

        data_flag = flag_data_confidence(r["readiness"], r["missing_weak_areas"])
        quality_flag = flag_quality(r["revenue_raw"], r["gross_profit_raw"], r["operating_income_raw"], fcf)
        balance_flag = flag_balance_sheet(r["cash_raw"], r["debt_raw"], r["current_ratio"], fcf)
        valuation_flag = flag_valuation(r["market_cap_raw"], r["enterprise_value_raw"], r["revenue_raw"], fcf, r["pe_ratio"], r["readiness"])
        dilution_flag = flag_dilution(r["dilution_1y"], r["dilution_3y"], r["sbc_raw"], r["revenue_raw"])
        data_score = score_data(r["readiness"], r["source_status"])
        peer_group = r["peer_group"] or r["category"] or ""
        red_flag_result, red_flags, watch_items, action = summarize_red_flags(
            data_flag,
            quality_flag,
            valuation_flag,
            balance_flag,
            dilution_flag,
            peer_group,
        )

        out.append({
            "Ticker": r["ticker"],
            "Review Status": red_flag_result,
            "Data Score": str(data_score),
            "Data Confidence Flag": data_flag,
            "Red Flag Result": red_flag_result,
            "Red Flags": red_flags,
            "Watch Items": watch_items,
            "Action": action,
            "Standalone Valuation Flag": valuation_flag,
            "Standalone Business Flag": quality_flag,
            "Standalone Balance Flag": balance_flag,
            "Standalone Dilution Flag": dilution_flag,
            "Company": r["company"] or "",
            "Category": r["category"] or "",
            "Peer Group": peer_group,
            "Price": fmt_price(r["price_per_share"]),
            "Market Cap": fmt_billions(r["market_cap_raw"]),
            "EV": fmt_billions(r["enterprise_value_raw"]),
            "Revenue": fmt_millions(r["revenue_raw"]),
            "FCF": fmt_millions(fcf),
            "Cash": fmt_millions(r["cash_raw"]),
            "Debt": fmt_millions(r["debt_raw"]),
            "Current Ratio": fmt_ratio(r["current_ratio"]),
            "Shares Out": fmt_shares_millions(r["shares_out_raw"]),
            "Diluted Shares": fmt_shares_millions(r["diluted_shares_raw"]),
            "Dilution 1Y": fmt_percent(r["dilution_1y"]),
            "Dilution 3Y": fmt_percent(r["dilution_3y"]),
            "EV/Revenue": fmt_ratio(ev_rev),
            "EV/FCF": fmt_ev_fcf(ev_fcf, fcf),
            "P/S": fmt_ratio(ps),
            "P/E": fmt_ratio(r["pe_ratio"]),
            "Beta": "" if r["beta"] is None else f"{float(r['beta']):,.2f}",
            "52W High": fmt_price(r["high_52w"]),
            "52W Low": fmt_price(r["low_52w"]),
            "Momentum Flag": r["price_momentum_flag"] or "",
            "Drawdown Flag": r["price_drawdown_flag"] or "",
            "Volatility Flag": r["price_volatility_flag"] or "",
            "1M Return": fmt_percent(r["price_return_1m"]),
            "3M Return": fmt_percent(r["price_return_3m"]),
            "6M Return": fmt_percent(r["price_return_6m"]),
            "1Y Return": fmt_percent(r["price_return_1y"]),
            "3Y Return": fmt_percent(r["price_return_3y"]),
            "From 52W High": fmt_percent(r["price_pct_from_52w_high"]),
            "90D Volatility": fmt_percent(r["price_volatility_90d"]),
            "Price Data Through": r["price_last_trade_date"] or "",
            "Cash Runway": "" if cash_runway is None else f"{cash_runway:,.2f} yrs",
            "Readiness": r["readiness"] or "",
            "Next Action": r["next_action"] or "",
            "Missing / Weak Areas": r["missing_weak_areas"] or "",
            "Source Status": r["source_status"] or "",
        })

    def sort_key(row: dict) -> tuple[int, int, str]:
        status = str(row.get("Review Status", ""))
        status_rank = 0
        if status.startswith("GREEN"):
            status_rank = 3
        elif status.startswith("YELLOW"):
            status_rank = 2
        elif status.startswith("RED"):
            status_rank = 1
        try:
            data_score = int(row.get("Data Score") or 0)
        except Exception:
            data_score = 0
        return (-status_rank, -data_score, str(row.get("Ticker", "")))

    return sorted(out, key=sort_key)
