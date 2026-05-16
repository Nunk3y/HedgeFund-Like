from __future__ import annotations

from app.db.database import get_connection


def present(value) -> bool:
    return value is not None


def status_present(value) -> str:
    return "OK" if present(value) else "MISSING"


def revenue_status(value) -> str:
    if value is None:
        return "MISSING"
    if value == 0:
        return "ZERO / PRE-REVENUE"
    return "OK"


def gross_profit_status(value, revenue) -> str:
    if value is None:
        return "MISSING"
    if value == 0 and revenue == 0:
        return "ZERO / PRE-REVENUE"
    if value == 0:
        return "ZERO"
    return "OK"


def fcf_status(value) -> str:
    if value is None:
        return "MISSING"
    if value < 0:
        return "NEGATIVE"
    return "OK"


def partial_expense_status(sbc, rd, sga) -> str:
    count = sum(1 for x in (sbc, rd, sga) if x is not None)
    if count == 3:
        return "OK"
    if count > 0:
        return "PARTIAL / OK"
    return "MISSING"


def calculate_model_readiness_for_ticker(ticker: str) -> None:
    ticker = ticker.upper().strip()
    conn = get_connection()
    md = conn.execute("SELECT * FROM market_data WHERE ticker = ?", (ticker,)).fetchone()
    if not md:
        conn.close()
        raise RuntimeError(f"No market_data row found for {ticker}. Normalize Market Data first.")

    price_ok = status_present(md["price_per_share"])
    market_cap_ok = status_present(md["market_cap_raw"])
    shares_ok = "OK" if md["shares_out_raw"] is not None or md["diluted_shares_raw"] is not None else "MISSING"
    rev_ok = revenue_status(md["revenue_raw"])
    gp_ok = gross_profit_status(md["gross_profit_raw"], md["revenue_raw"])
    ebitda_ok = status_present(md["ebitda_raw"])
    fcf_ok = fcf_status(md["fcf_raw"])
    cash_ok = status_present(md["cash_raw"])
    debt_ok = status_present(md["debt_raw"])
    liquidity_ok = status_present(md["current_ratio"])
    dilution_ok = "OK" if md["dilution_1y"] is not None and md["dilution_3y"] is not None else "MISSING"
    expense_ok = partial_expense_status(md["sbc_raw"], md["rd_raw"], md["sga_raw"])

    core_statuses = [price_ok, market_cap_ok, shares_ok, rev_ok, fcf_ok, cash_ok, debt_ok, liquidity_ok]
    core_ok_count = sum(1 for s in core_statuses if s in ("OK", "ZERO / PRE-REVENUE", "NEGATIVE"))
    core_score = core_ok_count / len(core_statuses)

    missing = []
    realities = []

    if price_ok != "OK": missing.append("Price")
    if market_cap_ok != "OK": missing.append("Market cap")
    if shares_ok != "OK": missing.append("Shares")
    if rev_ok == "MISSING": missing.append("Revenue")
    if gp_ok == "MISSING": missing.append("Gross profit")
    if ebitda_ok != "OK": missing.append("EBITDA")
    if fcf_ok == "MISSING": missing.append("FCF")
    if cash_ok != "OK": missing.append("Cash")
    if debt_ok != "OK": missing.append("Debt")
    if liquidity_ok != "OK": missing.append("Liquidity")
    if dilution_ok != "OK": missing.append("Historical dilution")
    if expense_ok == "MISSING": missing.append("SBC / R&D / SG&A")

    if rev_ok == "ZERO / PRE-REVENUE": realities.append("pre-revenue")
    if gp_ok in ("ZERO / PRE-REVENUE", "ZERO"): realities.append("zero gross profit")
    if fcf_ok == "NEGATIVE": realities.append("FCF-negative")
    if expense_ok == "PARTIAL / OK": realities.append("partial SBC/R&D/SG&A")

    if core_score < 0.6:
        readiness = "NOT SCREEN READY"
        next_action = "Pull or repair missing core market/financial data"
    elif rev_ok == "ZERO / PRE-REVENUE":
        readiness = "PARTIAL COMPARISON ONLY — PRE-REVENUE"
        next_action = "Use catalyst, cash runway, balance sheet, dilution, and peer context; skip DCF"
    elif fcf_ok == "NEGATIVE":
        readiness = "READY FOR DEEP-DIVE SCREENING — FCF NEGATIVE"
        next_action = "Compare against peers and verify cash runway, dilution risk, and catalysts"
    else:
        readiness = "READY FOR PEER COMPARISON"
        next_action = "Review peer valuation, quality, balance sheet, dilution, and catalysts"

    parts = []
    if missing:
        parts.append("Missing: " + ", ".join(missing))
    if realities:
        parts.append("Business realities: " + ", ".join(realities))
    missing_weak = " | ".join(parts) if parts else "None flagged"

    conn.execute(
        """
        INSERT INTO model_readiness (
            ticker, company, category, peer_group,
            price_ok, market_cap_ok, shares_ok, revenue_ok, gross_profit_ok,
            ebitda_ok, fcf_ok, cash_ok, debt_ok, liquidity_ok, dilution_ok,
            sbc_rd_sga_ok, core_data_score, readiness, next_action, missing_weak_areas,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(ticker) DO UPDATE SET
            company = excluded.company,
            category = excluded.category,
            peer_group = excluded.peer_group,
            price_ok = excluded.price_ok,
            market_cap_ok = excluded.market_cap_ok,
            shares_ok = excluded.shares_ok,
            revenue_ok = excluded.revenue_ok,
            gross_profit_ok = excluded.gross_profit_ok,
            ebitda_ok = excluded.ebitda_ok,
            fcf_ok = excluded.fcf_ok,
            cash_ok = excluded.cash_ok,
            debt_ok = excluded.debt_ok,
            liquidity_ok = excluded.liquidity_ok,
            dilution_ok = excluded.dilution_ok,
            sbc_rd_sga_ok = excluded.sbc_rd_sga_ok,
            core_data_score = excluded.core_data_score,
            readiness = excluded.readiness,
            next_action = excluded.next_action,
            missing_weak_areas = excluded.missing_weak_areas,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            ticker, md["company"], md["category"], md["peer_group"],
            price_ok, market_cap_ok, shares_ok, rev_ok, gp_ok,
            ebitda_ok, fcf_ok, cash_ok, debt_ok, liquidity_ok, dilution_ok,
            expense_ok, core_score, readiness, next_action, missing_weak,
        ),
    )
    conn.commit()
    conn.close()


def calculate_all_readiness() -> int:
    conn = get_connection()
    tickers = [r["ticker"] for r in conn.execute("SELECT ticker FROM market_data").fetchall()]
    conn.close()
    for ticker in tickers:
        calculate_model_readiness_for_ticker(ticker)
    return len(tickers)
