from __future__ import annotations

from typing import Optional

from app.db.database import get_connection


SEC_FIELD_TO_COL = {
    "revenue": "revenue_raw",
    "gross_profit": "gross_profit_raw",
    "operating_income": "operating_income_raw",
    "net_income": "net_income_raw",
    "eps_diluted": "eps_diluted",
    "operating_cash_flow": "operating_cash_flow_raw",
    "capital_expenditures": "capex_raw",
    "cash_and_equivalents": "cash_raw",
    "current_assets": "current_assets_raw",
    "current_liabilities": "current_liabilities_raw",
    "total_equity": "equity_raw",
    "share_based_compensation": "sbc_raw",
    "research_and_development": "rd_raw",
    "selling_general_admin": "sga_raw",
    "shares_diluted": "diluted_shares_raw",
    "dilution_1y": "dilution_1y",
    "dilution_3y": "dilution_3y",
}


def to_float(value) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "null":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def latest_ok_value(conn, ticker: str, raw_field: str, source: str | None = None, endpoint: str | None = None) -> Optional[float]:
    clauses = ["ticker = ?", "raw_field = ?", "status = 'OK'", "raw_value IS NOT NULL", "raw_value <> ''"]
    params = [ticker, raw_field]
    if source:
        clauses.append("source = ?")
        params.append(source)
    if endpoint:
        clauses.append("endpoint = ?")
        params.append(endpoint)
    sql = f"""
        SELECT raw_value
        FROM api_cache
        WHERE {' AND '.join(clauses)}
        ORDER BY id DESC
        LIMIT 1
    """
    row = conn.execute(sql, params).fetchone()
    return to_float(row["raw_value"]) if row else None


def latest_ok_text(conn, ticker: str, raw_field: str, source: str | None = None, endpoint: str | None = None) -> Optional[str]:
    clauses = ["ticker = ?", "raw_field = ?", "status = 'OK'", "raw_value IS NOT NULL", "raw_value <> ''"]
    params = [ticker, raw_field]
    if source:
        clauses.append("source = ?")
        params.append(source)
    if endpoint:
        clauses.append("endpoint = ?")
        params.append(endpoint)
    sql = f"SELECT raw_value FROM api_cache WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT 1"
    row = conn.execute(sql, params).fetchone()
    return str(row["raw_value"]) if row else None


def latest_ok_value_like(conn, ticker: str, raw_field_candidates: list[str], source: str | None = None, endpoint: str | None = None) -> Optional[float]:
    for field in raw_field_candidates:
        val = latest_ok_value(conn, ticker, field, source, endpoint)
        if val is not None:
            return val
    for field in raw_field_candidates:
        clauses = ["ticker = ?", "status = 'OK'", "raw_value IS NOT NULL", "raw_value <> ''"]
        params = [ticker]
        if source:
            clauses.append("source = ?")
            params.append(source)
        if endpoint:
            clauses.append("endpoint = ?")
            params.append(endpoint)
        clauses.append("(raw_field = ? OR raw_field LIKE ?)")
        params.extend([field, f"%.{field}"])
        sql = f"SELECT raw_value FROM api_cache WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT 1"
        row = conn.execute(sql, params).fetchone()
        if row:
            val = to_float(row["raw_value"])
            if val is not None:
                return val
    return None


def normalize_market_data_for_ticker(ticker: str) -> None:
    ticker = ticker.upper().strip()
    conn = get_connection()

    trow = conn.execute("SELECT ticker, company, category, peer_group, subsector FROM tickers WHERE ticker = ?", (ticker,)).fetchone()
    if not trow:
        conn.close()
        raise RuntimeError(f"Ticker not found in ticker table: {ticker}")

    company = trow["company"] or latest_ok_text(conn, ticker, "name", "FINNHUB", "profile2") or ""
    category = trow["category"] or ""
    peer_group = trow["peer_group"] or category
    subsector = trow["subsector"] or latest_ok_text(conn, ticker, "finnhubIndustry", "FINNHUB", "profile2") or ""

    values = {
        "ticker": ticker,
        "company": company,
        "category": category,
        "peer_group": peer_group,
        "subsector": subsector,
        "price_per_share": None,
        "market_cap_raw": None,
        "enterprise_value_raw": None,
        "shares_out_raw": None,
        "diluted_shares_raw": None,
        "high_52w": None,
        "low_52w": None,
        "beta": None,
        "avg_volume_shares": None,
        "pe_ratio": None,
        "eps_market": None,
        "revenue_raw": None,
        "gross_profit_raw": None,
        "operating_income_raw": None,
        "ebitda_raw": None,
        "net_income_raw": None,
        "eps_diluted": None,
        "operating_cash_flow_raw": None,
        "capex_raw": None,
        "fcf_raw": None,
        "cash_raw": None,
        "debt_raw": None,
        "net_debt_raw": None,
        "current_assets_raw": None,
        "current_liabilities_raw": None,
        "current_ratio": None,
        "equity_raw": None,
        "sbc_raw": None,
        "rd_raw": None,
        "sga_raw": None,
        "dilution_1y": None,
        "dilution_3y": None,
        "source_status": "",
    }

    for raw_field, col in SEC_FIELD_TO_COL.items():
        values[col] = latest_ok_value(conn, ticker, raw_field, "SEC EDGAR")

    if values.get("diluted_shares_raw") is None:
        values["diluted_shares_raw"] = latest_ok_value(conn, ticker, "shares_latest_for_dilution", "SEC EDGAR")

    values["price_per_share"] = latest_ok_value_like(conn, ticker, ["c", "current", "price"], "FINNHUB", "quote")

    market_cap_mm = latest_ok_value_like(conn, ticker, ["marketCapitalization", "metric.marketCapitalization"], "FINNHUB")
    values["market_cap_raw"] = market_cap_mm * 1_000_000 if market_cap_mm is not None else None

    shares_out_mm = latest_ok_value_like(conn, ticker, ["shareOutstanding", "metric.shareOutstanding"], "FINNHUB")
    values["shares_out_raw"] = shares_out_mm * 1_000_000 if shares_out_mm is not None else None

    values["high_52w"] = latest_ok_value_like(conn, ticker, ["metric.52WeekHigh", "52WeekHigh"], "FINNHUB")
    values["low_52w"] = latest_ok_value_like(conn, ticker, ["metric.52WeekLow", "52WeekLow"], "FINNHUB")
    values["beta"] = latest_ok_value_like(conn, ticker, ["metric.beta", "beta"], "FINNHUB")
    avg_vol_m = latest_ok_value_like(conn, ticker, ["metric.10DayAverageTradingVolume", "10DayAverageTradingVolume"], "FINNHUB")
    values["avg_volume_shares"] = avg_vol_m * 1_000_000 if avg_vol_m is not None else None
    values["pe_ratio"] = latest_ok_value_like(conn, ticker, [
        "metric.peNormalizedAnnual", "peNormalizedAnnual",
        "metric.peTTM", "peTTM",
        "metric.peBasicExclExtraTTM", "peBasicExclExtraTTM",
        "metric.peExclExtraAnnual", "peExclExtraAnnual",
        "metric.peInclExtraTTM", "peInclExtraTTM",
    ], "FINNHUB")
    values["eps_market"] = latest_ok_value_like(conn, ticker, ["metric.epsNormalizedAnnual", "epsNormalizedAnnual", "metric.epsTTM", "epsTTM"], "FINNHUB")

    if values["revenue_raw"] is None and values["shares_out_raw"] is not None:
        rev_per_share = (
            latest_ok_value(conn, ticker, "metric.revenuePerShareAnnual", "FINNHUB", "metric")
            or latest_ok_value(conn, ticker, "metric.revenuePerShareTTM", "FINNHUB", "metric")
        )
        if rev_per_share is not None:
            values["revenue_raw"] = rev_per_share * values["shares_out_raw"]

    if values["gross_profit_raw"] is None:
        cost_of_revenue = latest_ok_value(conn, ticker, "cost_of_revenue", "SEC EDGAR")
        if values["revenue_raw"] is not None and cost_of_revenue is not None:
            values["gross_profit_raw"] = values["revenue_raw"] - abs(cost_of_revenue)

    if values["gross_profit_raw"] is None:
        op_income = values.get("operating_income_raw")
        rd = values.get("rd_raw")
        sga = values.get("sga_raw")
        if op_income is not None and rd is not None and sga is not None:
            values["gross_profit_raw"] = op_income + abs(rd) + abs(sga)

    # Final gross-profit fallback: Finnhub gross margin * revenue.
    # This repairs companies where SEC CompanyFacts does not expose direct
    # GrossProfit or enough cost/expense concepts for reconstruction.
    if values["gross_profit_raw"] is None and values["revenue_raw"] is not None:
        gross_margin = latest_ok_value_like(conn, ticker, [
            "metric.grossMarginAnnual", "grossMarginAnnual",
            "metric.grossMarginTTM", "grossMarginTTM",
            "metric.grossMargin5Y", "grossMargin5Y",
        ], "FINNHUB", "metric")
        if gross_margin is not None:
            if gross_margin > 1:
                gross_margin = gross_margin / 100
            values["gross_profit_raw"] = values["revenue_raw"] * gross_margin

    if values["gross_profit_raw"] is None and values["revenue_raw"] == 0:
        values["gross_profit_raw"] = 0.0

    if values["ebitda_raw"] is None and values["shares_out_raw"] is not None:
        ebitda_per_share = (
            latest_ok_value(conn, ticker, "metric.ebitdPerShareAnnual", "FINNHUB", "metric")
            or latest_ok_value(conn, ticker, "metric.ebitdPerShareTTM", "FINNHUB", "metric")
        )
        if ebitda_per_share is not None:
            values["ebitda_raw"] = ebitda_per_share * values["shares_out_raw"]

    if values["ebitda_raw"] is None:
        da = latest_ok_value(conn, ticker, "depreciation_amortization", "SEC EDGAR")
        op_income = values.get("operating_income_raw")
        if da is not None and op_income is not None:
            values["ebitda_raw"] = op_income + da

    if values["market_cap_raw"] is None and values["price_per_share"] is not None and values["shares_out_raw"] is not None:
        values["market_cap_raw"] = values["price_per_share"] * values["shares_out_raw"]

    debt_current = latest_ok_value(conn, ticker, "debt_current", "SEC EDGAR") or 0.0
    debt_noncurrent = latest_ok_value(conn, ticker, "debt_noncurrent", "SEC EDGAR") or 0.0
    debt_total = latest_ok_value(conn, ticker, "total_debt_derived", "SEC EDGAR")
    if debt_total is None:
        debt_total = debt_current + debt_noncurrent
    values["debt_raw"] = debt_total

    ocf = values.get("operating_cash_flow_raw")
    capex = values.get("capex_raw")
    if ocf is not None and capex is not None:
        values["fcf_raw"] = ocf + capex if capex < 0 else ocf - capex

    cash = values.get("cash_raw")
    debt = values.get("debt_raw")
    values["net_debt_raw"] = (debt - cash) if cash is not None and debt is not None else None

    ca = values.get("current_assets_raw")
    cl = values.get("current_liabilities_raw")
    values["current_ratio"] = (ca / cl) if ca is not None and cl not in (None, 0) else None

    if values["market_cap_raw"] is not None and values["net_debt_raw"] is not None:
        values["enterprise_value_raw"] = values["market_cap_raw"] + values["net_debt_raw"]

    sources = conn.execute("SELECT DISTINCT source FROM api_cache WHERE ticker = ? AND status = 'OK' ORDER BY source", (ticker,)).fetchall()
    values["source_status"] = " + ".join([r["source"] for r in sources]) if sources else "NO OK CACHE DATA"

    conn.execute(
        """
        INSERT INTO market_data (
            ticker, company, category, peer_group, subsector,
            price_per_share, market_cap_raw, enterprise_value_raw,
            shares_out_raw, diluted_shares_raw,
            high_52w, low_52w, beta, avg_volume_shares, pe_ratio, eps_market,
            revenue_raw, gross_profit_raw, operating_income_raw,
            ebitda_raw, net_income_raw, eps_diluted,
            operating_cash_flow_raw, capex_raw, fcf_raw,
            cash_raw, debt_raw, net_debt_raw,
            current_assets_raw, current_liabilities_raw, current_ratio, equity_raw,
            sbc_raw, rd_raw, sga_raw,
            dilution_1y, dilution_3y,
            source_status, updated_at
        )
        VALUES (
            :ticker, :company, :category, :peer_group, :subsector,
            :price_per_share, :market_cap_raw, :enterprise_value_raw,
            :shares_out_raw, :diluted_shares_raw,
            :high_52w, :low_52w, :beta, :avg_volume_shares, :pe_ratio, :eps_market,
            :revenue_raw, :gross_profit_raw, :operating_income_raw,
            :ebitda_raw, :net_income_raw, :eps_diluted,
            :operating_cash_flow_raw, :capex_raw, :fcf_raw,
            :cash_raw, :debt_raw, :net_debt_raw,
            :current_assets_raw, :current_liabilities_raw, :current_ratio, :equity_raw,
            :sbc_raw, :rd_raw, :sga_raw,
            :dilution_1y, :dilution_3y,
            :source_status, CURRENT_TIMESTAMP
        )
        ON CONFLICT(ticker) DO UPDATE SET
            company = excluded.company,
            category = excluded.category,
            peer_group = excluded.peer_group,
            subsector = excluded.subsector,
            price_per_share = excluded.price_per_share,
            market_cap_raw = excluded.market_cap_raw,
            enterprise_value_raw = excluded.enterprise_value_raw,
            shares_out_raw = excluded.shares_out_raw,
            diluted_shares_raw = excluded.diluted_shares_raw,
            high_52w = excluded.high_52w,
            low_52w = excluded.low_52w,
            beta = excluded.beta,
            avg_volume_shares = excluded.avg_volume_shares,
            pe_ratio = excluded.pe_ratio,
            eps_market = excluded.eps_market,
            revenue_raw = excluded.revenue_raw,
            gross_profit_raw = excluded.gross_profit_raw,
            operating_income_raw = excluded.operating_income_raw,
            ebitda_raw = excluded.ebitda_raw,
            net_income_raw = excluded.net_income_raw,
            eps_diluted = excluded.eps_diluted,
            operating_cash_flow_raw = excluded.operating_cash_flow_raw,
            capex_raw = excluded.capex_raw,
            fcf_raw = excluded.fcf_raw,
            cash_raw = excluded.cash_raw,
            debt_raw = excluded.debt_raw,
            net_debt_raw = excluded.net_debt_raw,
            current_assets_raw = excluded.current_assets_raw,
            current_liabilities_raw = excluded.current_liabilities_raw,
            current_ratio = excluded.current_ratio,
            equity_raw = excluded.equity_raw,
            sbc_raw = excluded.sbc_raw,
            rd_raw = excluded.rd_raw,
            sga_raw = excluded.sga_raw,
            dilution_1y = excluded.dilution_1y,
            dilution_3y = excluded.dilution_3y,
            source_status = excluded.source_status,
            updated_at = CURRENT_TIMESTAMP
        """,
        values,
    )
    conn.commit()
    conn.close()


def normalize_all_market_data() -> int:
    conn = get_connection()
    tickers = [r["ticker"] for r in conn.execute("SELECT ticker FROM tickers WHERE status = 'active'").fetchall()]
    conn.close()
    for ticker in tickers:
        normalize_market_data_for_ticker(ticker)
    return len(tickers)