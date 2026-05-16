from __future__ import annotations

from app.db.database import get_connection
from app.services.flag_service import (
    flag_data_confidence,
    flag_balance_sheet,
    flag_quality,
    flag_valuation,
    flag_dilution,
    flag_overall,
    deep_dive_action,
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


def clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def score_data(readiness: str | None, source_status: str | None) -> int:
    readiness = readiness or ""
    source_status = source_status or ""
    if "MODEL READY" in readiness:
        return 100
    if "PARTIAL" in readiness:
        return 70
    if "PRE-REVENUE" in readiness:
        return 55
    if source_status:
        return 45
    return 20


def score_quality(revenue, gross_profit, operating_income, fcf) -> int:
    revenue = safe_float(revenue)
    gross_profit = safe_float(gross_profit)
    operating_income = safe_float(operating_income)
    fcf = safe_float(fcf)

    if revenue in (None, 0):
        return 35

    gross_margin = safe_multiple(gross_profit, revenue)
    operating_margin = safe_multiple(operating_income, revenue)
    fcf_margin = safe_multiple(fcf, revenue)

    score = 40
    if gross_margin is not None:
        if gross_margin >= 0.65:
            score += 20
        elif gross_margin >= 0.45:
            score += 12
        elif gross_margin >= 0.25:
            score += 5
        else:
            score -= 8

    if operating_margin is not None:
        if operating_margin >= 0.30:
            score += 20
        elif operating_margin >= 0.15:
            score += 12
        elif operating_margin >= 0:
            score += 4
        else:
            score -= 12

    if fcf_margin is not None:
        if fcf_margin >= 0.25:
            score += 20
        elif fcf_margin >= 0.10:
            score += 12
        elif fcf_margin >= 0:
            score += 4
        else:
            score -= 15

    return clamp_score(score)


def score_valuation(ev_rev, ev_fcf, ps, pe_ratio, fcf) -> int:
    fcf = safe_float(fcf)
    ev_rev = safe_float(ev_rev)
    ev_fcf = safe_float(ev_fcf)
    ps = safe_float(ps)
    pe_ratio = safe_float(pe_ratio)

    score = 50
    if fcf is not None and fcf <= 0:
        score -= 25

    if ev_fcf is not None and ev_fcf > 0:
        if ev_fcf <= 15:
            score += 25
        elif ev_fcf <= 25:
            score += 15
        elif ev_fcf <= 40:
            score += 5
        else:
            score -= 10
    elif ev_rev is not None:
        if ev_rev <= 5:
            score += 18
        elif ev_rev <= 10:
            score += 8
        elif ev_rev <= 20:
            score -= 3
        else:
            score -= 15
    elif ps is not None:
        if ps <= 5:
            score += 12
        elif ps <= 10:
            score += 4
        elif ps > 20:
            score -= 12

    if pe_ratio is not None and pe_ratio > 0:
        if pe_ratio <= 20:
            score += 8
        elif pe_ratio > 60:
            score -= 8

    return clamp_score(score)


def score_balance_sheet(cash, debt, current_ratio, fcf) -> int:
    cash = safe_float(cash)
    debt = safe_float(debt)
    current_ratio = safe_float(current_ratio)
    fcf = safe_float(fcf)

    score = 50
    if cash is not None and debt is not None:
        if cash > debt:
            score += 25
        elif debt > cash * 2:
            score -= 20
        else:
            score += 5

    if current_ratio is not None:
        if current_ratio >= 2:
            score += 15
        elif current_ratio >= 1:
            score += 5
        else:
            score -= 15

    if fcf is not None:
        if fcf > 0:
            score += 10
        else:
            score -= 10

    return clamp_score(score)


def score_dilution(dilution_1y, dilution_3y, sbc, revenue) -> int:
    dilution_1y = safe_float(dilution_1y)
    dilution_3y = safe_float(dilution_3y)
    sbc = safe_float(sbc)
    revenue = safe_float(revenue)

    score = 75
    if dilution_1y is not None:
        if dilution_1y <= 0:
            score += 15
        elif dilution_1y <= 0.02:
            score += 5
        elif dilution_1y <= 0.05:
            score -= 10
        else:
            score -= 25

    if dilution_3y is not None:
        if dilution_3y <= 0.05:
            score += 10
        elif dilution_3y <= 0.15:
            score -= 5
        else:
            score -= 20

    sbc_ratio = safe_multiple(sbc, revenue)
    if sbc_ratio is not None:
        if sbc_ratio <= 0.05:
            score += 5
        elif sbc_ratio <= 0.15:
            score -= 5
        else:
            score -= 20

    return clamp_score(score)


def score_fcf(fcf, revenue) -> int:
    fcf = safe_float(fcf)
    revenue = safe_float(revenue)
    if fcf is None:
        return 20
    if revenue in (None, 0):
        return 50 if fcf > 0 else 25
    margin = fcf / revenue
    if margin >= 0.30:
        return 100
    if margin >= 0.20:
        return 90
    if margin >= 0.10:
        return 75
    if margin >= 0:
        return 60
    if margin >= -0.10:
        return 35
    return 15


def final_score(data_score, quality_score, valuation_score, balance_score, dilution_score, fcf_score) -> int:
    score = (
        data_score * 0.15
        + quality_score * 0.25
        + valuation_score * 0.20
        + balance_score * 0.15
        + dilution_score * 0.10
        + fcf_score * 0.15
    )
    return clamp_score(score)


def rank_label(score: int, overall_flag: str) -> str:
    if overall_flag.startswith("GRAY"):
        return "NEEDS DATA"
    if score >= 80:
        return "A — Deep Dive"
    if score >= 65:
        return "B — Watch Closely"
    if score >= 50:
        return "C — Monitor"
    return "D — Low Priority"


def list_master_watchlist():
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            md.*,
            mr.readiness,
            mr.next_action,
            mr.missing_weak_areas,
            mr.core_data_score
        FROM market_data md
        LEFT JOIN model_readiness mr ON mr.ticker = md.ticker
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
        overall_flag = flag_overall(r["readiness"], data_flag, valuation_flag, quality_flag, balance_flag, dilution_flag, r["missing_weak_areas"])

        data_score = score_data(r["readiness"], r["source_status"])
        quality_score = score_quality(r["revenue_raw"], r["gross_profit_raw"], r["operating_income_raw"], fcf)
        valuation_score = score_valuation(ev_rev, ev_fcf, ps, r["pe_ratio"], fcf)
        balance_score = score_balance_sheet(r["cash_raw"], r["debt_raw"], r["current_ratio"], fcf)
        dilution_score = score_dilution(r["dilution_1y"], r["dilution_3y"], r["sbc_raw"], r["revenue_raw"])
        fcf_score = score_fcf(fcf, r["revenue_raw"])
        total_score = final_score(data_score, quality_score, valuation_score, balance_score, dilution_score, fcf_score)

        out.append({
            "Ticker": r["ticker"],
            "Final Rank": rank_label(total_score, overall_flag),
            "Score": str(total_score),
            "Quality Score": str(quality_score),
            "Valuation Score": str(valuation_score),
            "Balance Score": str(balance_score),
            "Dilution Score": str(dilution_score),
            "FCF Score": str(fcf_score),
            "Data Score": str(data_score),
            "Overall Flag": overall_flag,
            "Deep Dive Action": deep_dive_action(overall_flag),
            "Valuation Flag": valuation_flag,
            "Quality Flag": quality_flag,
            "Balance Sheet Flag": balance_flag,
            "Dilution Flag": dilution_flag,
            "Data Confidence Flag": data_flag,
            "Company": r["company"] or "",
            "Category": r["category"] or "",
            "Peer Group": r["peer_group"] or r["category"] or "",
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
            "Cash Runway": "" if cash_runway is None else f"{cash_runway:,.2f} yrs",
            "Readiness": r["readiness"] or "",
            "Next Action": r["next_action"] or "",
            "Missing / Weak Areas": r["missing_weak_areas"] or "",
            "Source Status": r["source_status"] or "",
        })

    return sorted(out, key=lambda row: int(row.get("Score") or 0), reverse=True)
