from __future__ import annotations

from typing import Optional


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def flag_data_confidence(readiness: str | None, missing: str | None) -> str:
    readiness = readiness or ""
    missing = missing or ""
    if "NOT MODEL READY" in readiness:
        return "GRAY — Insufficient Data"
    if "Missing:" in missing and any(x in missing for x in ["Price", "Market cap", "Shares", "Cash", "Debt"]):
        return "GRAY — Core Data Missing"
    return "GREEN — Data Usable"


def flag_balance_sheet(cash, debt, current_ratio, fcf) -> str:
    cash = safe_float(cash)
    debt = safe_float(debt)
    current_ratio = safe_float(current_ratio)
    fcf = safe_float(fcf)

    if cash is None or debt is None:
        return "GRAY — Missing Balance Sheet"

    if fcf is not None and fcf < 0:
        # runway years
        runway = abs(cash / fcf) if fcf != 0 else None
        if runway is not None and runway >= 5:
            return "GREEN — Strong Runway"
        if runway is not None and runway >= 2:
            return "YELLOW — Adequate Runway"
        return "RED — Weak Runway"

    if debt == 0 and cash > 0:
        return "GREEN — Net Cash"

    if cash > debt and (current_ratio is None or current_ratio >= 1.5):
        return "GREEN — Strong Balance Sheet"

    if current_ratio is not None and current_ratio < 1:
        return "RED — Liquidity Risk"

    if debt > cash:
        return "YELLOW — Debt Watch"

    return "YELLOW — Review Balance Sheet"


def flag_quality(revenue, gross_profit, operating_income, fcf, gross_margin=None, fcf_margin=None) -> str:
    revenue = safe_float(revenue)
    gross_profit = safe_float(gross_profit)
    operating_income = safe_float(operating_income)
    fcf = safe_float(fcf)

    if revenue is None:
        return "GRAY — Missing Revenue"
    if revenue == 0:
        return "PURPLE — Pre-Revenue"
    if fcf is None:
        return "YELLOW — Missing FCF"
    if fcf < 0:
        return "RED — FCF Negative"
    if operating_income is not None and operating_income > 0 and fcf > 0:
        return "GREEN — Profitable / FCF Positive"
    if gross_profit is not None and gross_profit > 0 and fcf > 0:
        return "YELLOW — FCF Positive"
    return "YELLOW — Mixed Quality"


def flag_valuation(market_cap, enterprise_value, revenue, fcf, pe_ratio, readiness) -> str:
    market_cap = safe_float(market_cap)
    ev = safe_float(enterprise_value)
    revenue = safe_float(revenue)
    fcf = safe_float(fcf)
    pe = safe_float(pe_ratio)
    readiness = readiness or ""

    if "PARTIAL MODEL ONLY" in readiness:
        return "PURPLE — Normal Valuation Weak"

    # Use rough absolute guards until peer medians exist.
    ev_rev = ev / revenue if ev is not None and revenue not in (None, 0) else None
    ev_fcf = ev / fcf if ev is not None and fcf not in (None, 0) else None

    if ev_rev is None and pe is None and ev_fcf is None:
        return "GRAY — Missing Valuation Data"

    risk_points = 0
    good_points = 0

    if ev_rev is not None:
        if ev_rev > 25:
            risk_points += 2
        elif ev_rev > 12:
            risk_points += 1
        elif ev_rev < 6:
            good_points += 1

    if pe is not None:
        if pe > 60:
            risk_points += 2
        elif pe > 35:
            risk_points += 1
        elif 0 < pe < 25:
            good_points += 1

    if ev_fcf is not None and ev_fcf > 0:
        if ev_fcf > 60:
            risk_points += 2
        elif ev_fcf > 35:
            risk_points += 1
        elif ev_fcf < 25:
            good_points += 1

    if risk_points >= 3:
        return "RED — Expensive"
    if risk_points >= 1:
        return "YELLOW — Valuation Risk"
    if good_points >= 2:
        return "GREEN — Reasonable Valuation"
    return "YELLOW — Review Valuation"


def flag_dilution(dilution_1y, dilution_3y, sbc, revenue) -> str:
    d1 = safe_float(dilution_1y)
    d3 = safe_float(dilution_3y)
    sbc = safe_float(sbc)
    revenue = safe_float(revenue)

    if d1 is None and d3 is None:
        return "GRAY — Missing Dilution"

    if d1 is not None and d1 > 0.20:
        return "RED — High Dilution"
    if d3 is not None and d3 > 0.50:
        return "RED — High 3Y Dilution"

    if sbc is not None and revenue not in (None, 0):
        sbc_pct_rev = sbc / revenue
        if sbc_pct_rev > 0.20:
            return "RED — High SBC"
        if sbc_pct_rev > 0.10:
            return "YELLOW — SBC Watch"

    if (d1 is not None and d1 > 0.05) or (d3 is not None and d3 > 0.15):
        return "YELLOW — Dilution Watch"

    return "GREEN — Dilution OK"


def flag_overall(readiness, data_flag, valuation_flag, quality_flag, balance_flag, dilution_flag, missing_weak) -> str:
    readiness = readiness or ""
    missing_weak = missing_weak or ""

    flags = [data_flag, valuation_flag, quality_flag, balance_flag, dilution_flag]
    if any(f.startswith("GRAY") for f in flags) and "PARTIAL MODEL ONLY" not in readiness:
        return "GRAY — Insufficient Data"

    if "pre-revenue" in missing_weak.lower() or "PARTIAL MODEL ONLY" in readiness:
        if balance_flag.startswith("GREEN") or balance_flag.startswith("YELLOW"):
            return "PURPLE — Speculative Catalyst Only"
        return "RED — Speculative / Weak Balance Sheet"

    red_count = sum(1 for f in flags if f.startswith("RED"))
    yellow_count = sum(1 for f in flags if f.startswith("YELLOW"))
    green_count = sum(1 for f in flags if f.startswith("GREEN"))

    if red_count >= 2:
        return "RED — Skip / Too Weak"
    if red_count == 1:
        return "YELLOW — Watch / Needs Context"
    if green_count >= 3 and yellow_count <= 2:
        return "GREEN — Deep Dive Candidate"
    return "YELLOW — Watch / Needs Catalyst"


def deep_dive_action(overall_flag: str) -> str:
    if overall_flag.startswith("GREEN"):
        return "Deep dive"
    if overall_flag.startswith("PURPLE"):
        return "Speculative catalyst research only"
    if overall_flag.startswith("YELLOW"):
        return "Watch; look for catalyst or peer discount"
    if overall_flag.startswith("GRAY"):
        return "Fix data before research"
    if overall_flag.startswith("RED"):
        return "Skip unless catalyst is exceptional"
    return "Review"
