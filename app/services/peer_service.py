from __future__ import annotations

from statistics import median
from typing import Optional

from app.db.database import get_connection


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_div(num, den) -> Optional[float]:
    num = safe_float(num)
    den = safe_float(den)
    if num is None or den in (None, 0):
        return None
    return num / den


def fmt_ratio(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):,.2f}x"
    except Exception:
        return ""


def fmt_ev_fcf(ev_fcf, fcf) -> str:
    fcf = safe_float(fcf)
    if fcf is None:
        return "MISSING FCF"
    if fcf < 0:
        return "NEG FCF"
    if fcf == 0:
        return "ZERO FCF"
    return fmt_ratio(ev_fcf)


def fmt_percent(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value) * 100:,.2f}%"
    except Exception:
        return ""


def fmt_number(value) -> str:
    if value is None:
        return ""
    try:
        return f"{float(value):,.3f}"
    except Exception:
        return ""


def clean_group(value: str | None, fallback: str | None = None) -> str:
    value = (value or "").strip()
    fallback = (fallback or "").strip()
    if value:
        return value
    if fallback:
        return fallback
    return "Unassigned"


def median_or_none(values):
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return median(clean)


def flag_relative_lower_is_better(value, peer_median, metric_name: str) -> str:
    value = safe_float(value)
    peer_median = safe_float(peer_median)
    if value is None or peer_median in (None, 0):
        return "GRAY — No Peer Benchmark"

    ratio = value / peer_median
    if ratio <= 0.75:
        return "GREEN — Cheap vs Peers"
    if ratio <= 1.25:
        return "YELLOW — Near Peer Median"
    return "RED — Expensive vs Peers"


def flag_relative_higher_is_better(value, peer_median, metric_name: str) -> str:
    value = safe_float(value)
    peer_median = safe_float(peer_median)
    if value is None or peer_median in (None, 0):
        return "GRAY — No Peer Benchmark"

    ratio = value / peer_median
    if ratio >= 1.25:
        return "GREEN — Strong vs Peers"
    if ratio >= 0.75:
        return "YELLOW — Near Peer Median"
    return "RED — Weak vs Peers"


def overall_peer_flag(valuation_flag: str, quality_flag: str, balance_flag: str, peer_count: int, readiness: str | None) -> str:
    readiness = readiness or ""

    if peer_count < 2:
        return "GRAY — Need More Peers"

    if "PRE-REVENUE" in readiness:
        return "PURPLE — Speculative Peer Set"

    flags = [valuation_flag, quality_flag, balance_flag]
    red = sum(1 for f in flags if f.startswith("RED"))
    green = sum(1 for f in flags if f.startswith("GREEN"))

    if red >= 2:
        return "RED — Weak vs Peers"
    if green >= 2 and red == 0:
        return "GREEN — Strong Peer Setup"
    return "YELLOW — Mixed Peer Setup"


def list_peer_comparison():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            md.*,
            mr.readiness,
            mr.missing_weak_areas
        FROM market_data md
        LEFT JOIN model_readiness mr ON mr.ticker = md.ticker
        ORDER BY COALESCE(md.peer_group, md.category, 'Unassigned'), md.ticker
        """
    ).fetchall()
    conn.close()

    enriched = []
    for r in rows:
        revenue = safe_float(r["revenue_raw"])
        fcf = safe_float(r["fcf_raw"])
        ev = safe_float(r["enterprise_value_raw"])
        market_cap = safe_float(r["market_cap_raw"])
        cash = safe_float(r["cash_raw"])
        debt = safe_float(r["debt_raw"])
        current_ratio = safe_float(r["current_ratio"])
        operating_income = safe_float(r["operating_income_raw"])
        gross_profit = safe_float(r["gross_profit_raw"])

        ev_rev = safe_div(ev, revenue)
        ev_fcf = safe_div(ev, fcf) if fcf and fcf > 0 else None
        ps = safe_div(market_cap, revenue)
        fcf_margin = safe_div(fcf, revenue)
        op_margin = safe_div(operating_income, revenue)
        gross_margin = safe_div(gross_profit, revenue)
        net_cash = None
        if cash is not None and debt is not None:
            net_cash = cash - debt

        enriched.append({
            "row": r,
            "peer_group": clean_group(r["peer_group"], r["category"]),
            "ev_rev": ev_rev,
            "ev_fcf": ev_fcf,
            "fcf_raw": fcf,
            "ps": ps,
            "fcf_margin": fcf_margin,
            "op_margin": op_margin,
            "gross_margin": gross_margin,
            "current_ratio": current_ratio,
            "net_cash": net_cash,
        })

    groups = {}
    for item in enriched:
        groups.setdefault(item["peer_group"], []).append(item)

    group_stats = {}
    for group, items in groups.items():
        group_stats[group] = {
            "count": len(items),
            "ev_rev_median": median_or_none([i["ev_rev"] for i in items]),
            "ev_fcf_median": median_or_none([i["ev_fcf"] for i in items]),
            "ps_median": median_or_none([i["ps"] for i in items]),
            "fcf_margin_median": median_or_none([i["fcf_margin"] for i in items]),
            "op_margin_median": median_or_none([i["op_margin"] for i in items]),
            "gross_margin_median": median_or_none([i["gross_margin"] for i in items]),
            "current_ratio_median": median_or_none([i["current_ratio"] for i in items]),
        }

    out = []
    for item in enriched:
        r = item["row"]
        stats = group_stats[item["peer_group"]]
        peer_count = stats["count"]

        valuation_flag = flag_relative_lower_is_better(item["ev_rev"], stats["ev_rev_median"], "EV/Revenue")
        if valuation_flag.startswith("GRAY"):
            valuation_flag = flag_relative_lower_is_better(item["ps"], stats["ps_median"], "P/S")

        quality_value = item["fcf_margin"]
        quality_median = stats["fcf_margin_median"]
        if quality_value is None or quality_median is None:
            quality_value = item["op_margin"]
            quality_median = stats["op_margin_median"]
        if quality_value is None or quality_median is None:
            quality_value = item["gross_margin"]
            quality_median = stats["gross_margin_median"]
        quality_flag = flag_relative_higher_is_better(quality_value, quality_median, "Margin")

        balance_flag = flag_relative_higher_is_better(item["current_ratio"], stats["current_ratio_median"], "Current Ratio")
        peer_flag = overall_peer_flag(valuation_flag, quality_flag, balance_flag, peer_count, r["readiness"])

        out.append({
            "Ticker": r["ticker"],
            "Peer Group": item["peer_group"],
            "Peer Count": str(peer_count),
            "Overall Peer Flag": peer_flag,
            "Relative Valuation Flag": valuation_flag,
            "Relative Quality Flag": quality_flag,
            "Relative Balance Flag": balance_flag,
            "EV/Revenue": fmt_ratio(item["ev_rev"]),
            "Peer Median EV/Revenue": fmt_ratio(stats["ev_rev_median"]),
            "EV/FCF": fmt_ev_fcf(item["ev_fcf"], item["fcf_raw"]),
            "Peer Median EV/FCF": fmt_ratio(stats["ev_fcf_median"]),
            "P/S": fmt_ratio(item["ps"]),
            "Peer Median P/S": fmt_ratio(stats["ps_median"]),
            "FCF Margin": fmt_percent(item["fcf_margin"]),
            "Peer Median FCF Margin": fmt_percent(stats["fcf_margin_median"]),
            "Operating Margin": fmt_percent(item["op_margin"]),
            "Peer Median Operating Margin": fmt_percent(stats["op_margin_median"]),
            "Gross Margin": fmt_percent(item["gross_margin"]),
            "Peer Median Gross Margin": fmt_percent(stats["gross_margin_median"]),
            "Current Ratio": fmt_number(item["current_ratio"]),
            "Peer Median Current Ratio": fmt_number(stats["current_ratio_median"]),
            "Readiness": r["readiness"] or "",
            "Missing / Weak Areas": r["missing_weak_areas"] or "",
        })

    return out
