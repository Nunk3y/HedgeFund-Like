from __future__ import annotations

from app.db.database import get_connection
from app.services.flag_service import (
    deep_dive_action,
    flag_balance_sheet,
    flag_data_confidence,
    flag_dilution,
    flag_overall,
    flag_quality,
    flag_valuation,
)
from app.services.watchlist_service import (
    final_score,
    fmt_millions,
    fmt_percent,
    fmt_ratio,
    rank_label,
    risk_adjusted_score,
    safe_float,
    safe_multiple,
    score_balance_sheet,
    score_data,
    score_dilution,
    score_fcf,
    score_quality,
    score_valuation,
)


SCORE_WEIGHTS = {
    "Data": 0.15,
    "Quality": 0.25,
    "Valuation": 0.20,
    "Balance Sheet": 0.15,
    "Dilution": 0.10,
    "FCF": 0.15,
}
COMPONENT_ORDER = {component: idx for idx, component in enumerate(SCORE_WEIGHTS)}


def weighted_points(score: int, component: str) -> float:
    return round(score * SCORE_WEIGHTS[component], 2)


def row_value(row, key: str):
    return row[key] if key in row.keys() else None


def describe_data(readiness: str | None, source_status: str | None, missing: str | None) -> str:
    readiness = readiness or "No readiness row"
    source_status = source_status or "No OK source"
    missing = missing or "None flagged"
    return f"Readiness: {readiness}. Sources: {source_status}. Missing/weak: {missing}."


def describe_quality(revenue, gross_profit, operating_income, fcf) -> str:
    gross_margin = safe_multiple(gross_profit, revenue)
    operating_margin = safe_multiple(operating_income, revenue)
    fcf_margin = safe_multiple(fcf, revenue)
    return (
        f"Revenue {fmt_millions(revenue)}, gross margin {fmt_percent(gross_margin)}, "
        f"operating margin {fmt_percent(operating_margin)}, FCF margin {fmt_percent(fcf_margin)}."
    )


def describe_valuation(ev_rev, ev_fcf, ps, pe_ratio, fcf) -> str:
    ev_fcf_text = "NEG/MISSING FCF" if ev_fcf is None and safe_float(fcf) is not None and safe_float(fcf) <= 0 else fmt_ratio(ev_fcf)
    return (
        f"EV/Revenue {fmt_ratio(ev_rev)}, EV/FCF {ev_fcf_text}, "
        f"P/S {fmt_ratio(ps)}, P/E {fmt_ratio(pe_ratio)}, FCF {fmt_millions(fcf)}."
    )


def describe_balance(cash, debt, current_ratio, fcf) -> str:
    net_cash = None
    cash_value = safe_float(cash)
    debt_value = safe_float(debt)
    if cash_value is not None and debt_value is not None:
        net_cash = cash_value - debt_value
    return (
        f"Cash {fmt_millions(cash)}, debt {fmt_millions(debt)}, "
        f"net cash {fmt_millions(net_cash)}, current ratio {fmt_ratio(current_ratio)}, FCF {fmt_millions(fcf)}."
    )


def describe_dilution(dilution_1y, dilution_3y, sbc, revenue) -> str:
    sbc_ratio = safe_multiple(sbc, revenue)
    return (
        f"Dilution 1Y {fmt_percent(dilution_1y)}, dilution 3Y {fmt_percent(dilution_3y)}, "
        f"SBC {fmt_millions(sbc)}, SBC/revenue {fmt_percent(sbc_ratio)}."
    )


def describe_fcf(fcf, revenue) -> str:
    fcf_margin = safe_multiple(fcf, revenue)
    return f"FCF {fmt_millions(fcf)}, revenue {fmt_millions(revenue)}, FCF margin {fmt_percent(fcf_margin)}."


def list_score_details(ticker: str | None = None) -> list[dict]:
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
            mr.next_action,
            mr.missing_weak_areas,
            mr.core_data_score
        FROM market_data md
        LEFT JOIN model_readiness mr ON mr.ticker = md.ticker
        {ticker_clause}
        ORDER BY md.ticker
        """,
        params,
    ).fetchall()
    conn.close()

    out = []
    for r in rows:
        fcf = safe_float(r["fcf_raw"])
        ev_rev = safe_multiple(r["enterprise_value_raw"], r["revenue_raw"])
        ev_fcf = safe_multiple(r["enterprise_value_raw"], fcf) if fcf and fcf > 0 else None
        ps = safe_multiple(r["market_cap_raw"], r["revenue_raw"])

        data_flag = flag_data_confidence(row_value(r, "readiness"), row_value(r, "missing_weak_areas"))
        quality_flag = flag_quality(r["revenue_raw"], r["gross_profit_raw"], r["operating_income_raw"], fcf)
        balance_flag = flag_balance_sheet(r["cash_raw"], r["debt_raw"], r["current_ratio"], fcf)
        valuation_flag = flag_valuation(r["market_cap_raw"], r["enterprise_value_raw"], r["revenue_raw"], fcf, r["pe_ratio"], row_value(r, "readiness"))
        dilution_flag = flag_dilution(r["dilution_1y"], r["dilution_3y"], r["sbc_raw"], r["revenue_raw"])
        overall_flag = flag_overall(row_value(r, "readiness"), data_flag, valuation_flag, quality_flag, balance_flag, dilution_flag, row_value(r, "missing_weak_areas"))

        scores = {
            "Data": score_data(row_value(r, "readiness"), r["source_status"]),
            "Quality": score_quality(r["revenue_raw"], r["gross_profit_raw"], r["operating_income_raw"], fcf),
            "Valuation": score_valuation(ev_rev, ev_fcf, ps, r["pe_ratio"], fcf),
            "Balance Sheet": score_balance_sheet(r["cash_raw"], r["debt_raw"], r["current_ratio"], fcf),
            "Dilution": score_dilution(r["dilution_1y"], r["dilution_3y"], r["sbc_raw"], r["revenue_raw"]),
            "FCF": score_fcf(fcf, r["revenue_raw"]),
        }
        raw_score = final_score(
            scores["Data"],
            scores["Quality"],
            scores["Valuation"],
            scores["Balance Sheet"],
            scores["Dilution"],
            scores["FCF"],
        )
        total_score = risk_adjusted_score(raw_score, overall_flag)

        component_data = [
            ("Data", data_flag, describe_data(row_value(r, "readiness"), r["source_status"], row_value(r, "missing_weak_areas"))),
            ("Quality", quality_flag, describe_quality(r["revenue_raw"], r["gross_profit_raw"], r["operating_income_raw"], fcf)),
            ("Valuation", valuation_flag, describe_valuation(ev_rev, ev_fcf, ps, r["pe_ratio"], fcf)),
            ("Balance Sheet", balance_flag, describe_balance(r["cash_raw"], r["debt_raw"], r["current_ratio"], fcf)),
            ("Dilution", dilution_flag, describe_dilution(r["dilution_1y"], r["dilution_3y"], r["sbc_raw"], r["revenue_raw"])),
            ("FCF", quality_flag if fcf is None else ("GREEN - FCF Strong" if scores["FCF"] >= 75 else "YELLOW - FCF Review" if scores["FCF"] >= 35 else "RED - FCF Weak"), describe_fcf(fcf, r["revenue_raw"])),
        ]

        for component, flag, rationale in component_data:
            out.append({
                "Ticker": r["ticker"],
                "Company": r["company"] or "",
                "Component": component,
                "Component Score": str(scores[component]),
                "Weight": fmt_percent(SCORE_WEIGHTS[component]),
                "Weighted Points": f"{weighted_points(scores[component], component):.2f}",
                "Flag": flag,
                "Inputs / Rationale": rationale,
                "Overall Score": str(total_score),
                "Raw Score": str(raw_score),
                "Final Rank": rank_label(total_score, overall_flag),
                "Overall Flag": overall_flag,
                "Deep Dive Action": deep_dive_action(overall_flag),
                "Readiness": row_value(r, "readiness") or "",
                "Missing / Weak Areas": row_value(r, "missing_weak_areas") or "",
            })

    return sorted(
        out,
        key=lambda item: (-int(item["Overall Score"]), item["Ticker"], COMPONENT_ORDER.get(item["Component"], 999)),
    )
