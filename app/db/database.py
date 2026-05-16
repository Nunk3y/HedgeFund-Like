import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path("tech_screener.db")

STARTER_TICKERS = [
    ("NVDA", "NVIDIA Corporation", "AI Hardware / Semiconductors"),
    ("AVGO", "Broadcom Inc.", "AI Hardware / Semiconductors"),
    ("AMD", "Advanced Micro Devices, Inc.", "AI Hardware / Semiconductors"),
    ("INTC", "Intel Corporation", "AI Hardware / Semiconductors"),
    ("TSM", "Taiwan Semiconductor Manufacturing Company Limited", "Semiconductor Manufacturing"),
    ("ASML", "ASML Holding N.V.", "Semiconductor Equipment"),
    ("ARM", "Arm Holdings plc", "Semiconductor IP"),
    ("MU", "Micron Technology, Inc.", "AI Hardware / Semiconductors"),
    ("MRVL", "Marvell Technology, Inc.", "AI Hardware / Semiconductors"),
    ("QCOM", "QUALCOMM Incorporated", "AI Hardware / Semiconductors"),
]

STARTER_TICKER_SET = {ticker for ticker, _, _ in STARTER_TICKERS}


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    for name, col_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {col_type}")


def ensure_app_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)


def get_deleted_starter_tickers(conn: sqlite3.Connection) -> set[str]:
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'deleted_starter_tickers'").fetchone()
    if not row or not row["value"]:
        return set()
    return {x.strip().upper() for x in row["value"].split(",") if x.strip()}


def set_deleted_starter_tickers(conn: sqlite3.Connection, tickers: set[str]) -> None:
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES ('deleted_starter_tickers', ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (",".join(sorted(tickers)),),
    )


def seed_starter_tickers(conn: sqlite3.Connection) -> None:
    deleted = get_deleted_starter_tickers(conn)
    rows = [(ticker, company, peer_group, peer_group) for ticker, company, peer_group in STARTER_TICKERS if ticker not in deleted]
    if not rows:
        return
    conn.executemany(
        """
        INSERT INTO tickers (ticker, company, category, peer_group, subsector)
        VALUES (?, ?, ?, ?, '')
        ON CONFLICT(ticker) DO UPDATE SET
            company = COALESCE(NULLIF(tickers.company, ''), excluded.company),
            category = COALESCE(NULLIF(tickers.category, ''), excluded.category),
            peer_group = COALESCE(NULLIF(tickers.peer_group, ''), excluded.peer_group),
            updated_at = CURRENT_TIMESTAMP
        """,
        rows,
    )


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickers (
        ticker TEXT PRIMARY KEY,
        company TEXT,
        category TEXT,
        peer_group TEXT,
        subsector TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        timestamp TEXT,
        source TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        raw_field TEXT NOT NULL,
        raw_value TEXT,
        period TEXT,
        fiscal_year TEXT,
        status TEXT,
        error_message TEXT,
        notes TEXT,
        cik TEXT,
        sec_concept TEXT,
        unit TEXT,
        form TEXT,
        filed TEXT,
        period_start TEXT,
        period_end TEXT,
        frame TEXT,
        accession TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_data (
        ticker TEXT PRIMARY KEY,
        company TEXT,
        category TEXT,
        peer_group TEXT,
        subsector TEXT,
        price_per_share REAL,
        market_cap_raw REAL,
        enterprise_value_raw REAL,
        shares_out_raw REAL,
        diluted_shares_raw REAL,
        high_52w REAL,
        low_52w REAL,
        beta REAL,
        avg_volume_shares REAL,
        pe_ratio REAL,
        eps_market REAL,
        revenue_raw REAL,
        gross_profit_raw REAL,
        operating_income_raw REAL,
        ebitda_raw REAL,
        net_income_raw REAL,
        eps_diluted REAL,
        operating_cash_flow_raw REAL,
        capex_raw REAL,
        fcf_raw REAL,
        cash_raw REAL,
        debt_raw REAL,
        net_debt_raw REAL,
        current_assets_raw REAL,
        current_liabilities_raw REAL,
        current_ratio REAL,
        equity_raw REAL,
        sbc_raw REAL,
        rd_raw REAL,
        sga_raw REAL,
        dilution_1y REAL,
        dilution_3y REAL,
        source_status TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS model_readiness (
        ticker TEXT PRIMARY KEY,
        company TEXT,
        category TEXT,
        peer_group TEXT,
        price_ok TEXT,
        market_cap_ok TEXT,
        shares_ok TEXT,
        revenue_ok TEXT,
        gross_profit_ok TEXT,
        ebitda_ok TEXT,
        fcf_ok TEXT,
        cash_ok TEXT,
        debt_ok TEXT,
        liquidity_ok TEXT,
        dilution_ok TEXT,
        sbc_rd_sga_ok TEXT,
        core_data_score REAL,
        readiness TEXT,
        next_action TEXT,
        missing_weak_areas TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assumptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        model_name TEXT NOT NULL,
        assumption_name TEXT NOT NULL,
        scenario TEXT,
        value REAL,
        text_value TEXT,
        source_url TEXT,
        source_note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    ensure_app_settings_table(conn)

    ensure_columns(conn, "tickers", {
        "peer_group": "TEXT",
        "subsector": "TEXT",
        "status": "TEXT DEFAULT 'active'",
        "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
        "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
    })

    ensure_columns(conn, "market_data", {
        "peer_group": "TEXT",
        "subsector": "TEXT",
        "high_52w": "REAL",
        "low_52w": "REAL",
        "beta": "REAL",
        "avg_volume_shares": "REAL",
        "pe_ratio": "REAL",
        "eps_market": "REAL",
    })

    ensure_columns(conn, "model_readiness", {"peer_group": "TEXT"})
    seed_starter_tickers(conn)

    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    ensure_app_settings_table(conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row and row["value"] is not None else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    ensure_app_settings_table(conn)
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
        """,
        (key, value),
    )
    conn.commit()
    conn.close()


def add_ticker(ticker: str, company: str = "", category: str = "", peer_group: str = "", subsector: str = "") -> None:
    ticker = ticker.upper().strip()
    conn = get_connection()
    if ticker in STARTER_TICKER_SET:
        deleted = get_deleted_starter_tickers(conn)
        if ticker in deleted:
            deleted.remove(ticker)
            set_deleted_starter_tickers(conn, deleted)
    conn.execute(
        """
        INSERT INTO tickers (ticker, company, category, peer_group, subsector)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(ticker) DO UPDATE SET
            company = COALESCE(NULLIF(excluded.company, ''), tickers.company),
            category = COALESCE(NULLIF(excluded.category, ''), tickers.category),
            peer_group = COALESCE(NULLIF(excluded.peer_group, ''), tickers.peer_group),
            subsector = COALESCE(NULLIF(excluded.subsector, ''), tickers.subsector),
            updated_at = CURRENT_TIMESTAMP
        """,
        (ticker, company, category, peer_group, subsector),
    )
    conn.commit()
    conn.close()


def delete_ticker(ticker: str, delete_cached_data: bool = True) -> None:
    ticker = ticker.upper().strip()
    conn = get_connection()
    ensure_app_settings_table(conn)

    if ticker in STARTER_TICKER_SET:
        deleted = get_deleted_starter_tickers(conn)
        deleted.add(ticker)
        set_deleted_starter_tickers(conn, deleted)

    conn.execute("DELETE FROM tickers WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM market_data WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM model_readiness WHERE ticker = ?", (ticker,))
    conn.execute("DELETE FROM assumptions WHERE ticker = ?", (ticker,))
    if delete_cached_data:
        conn.execute("DELETE FROM api_cache WHERE ticker = ?", (ticker,))

    conn.commit()
    conn.close()


def list_tickers():
    conn = get_connection()
    rows = conn.execute("SELECT ticker, company, category, peer_group, subsector, status FROM tickers ORDER BY ticker").fetchall()
    conn.close()
    return rows


def insert_api_cache_rows(rows: list[dict], replace_source_for_ticker: bool = True) -> None:
    if not rows:
        return
    ticker = rows[0].get("Ticker", "").upper().strip()
    source = rows[0].get("Source", "")
    conn = get_connection()
    if replace_source_for_ticker and ticker and source:
        conn.execute("DELETE FROM api_cache WHERE ticker = ? AND source = ?", (ticker, source))

    conn.executemany(
        """
        INSERT INTO api_cache (
            ticker, timestamp, source, endpoint, raw_field, raw_value,
            period, fiscal_year, status, error_message, notes, cik,
            sec_concept, unit, form, filed, period_start, period_end, frame, accession
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r.get("Ticker", ""), r.get("Timestamp", ""), r.get("Source", ""),
                r.get("Endpoint / Metric", ""), r.get("Raw Field", ""), str(r.get("Raw Value", "")),
                str(r.get("Period", "")), str(r.get("Fiscal Year", "")), r.get("Status", ""),
                r.get("Error Message", ""), r.get("Notes", ""), str(r.get("CIK", "")),
                r.get("SEC Concept", ""), r.get("Unit", ""), r.get("Form", ""), r.get("Filed", ""),
                r.get("Period Start", ""), r.get("Period End", ""), r.get("Frame", ""), r.get("Accession", ""),
            )
            for r in rows
        ],
    )
    conn.commit()
    conn.close()


def list_api_cache(ticker: Optional[str] = None, limit: int = 500):
    conn = get_connection()
    if ticker:
        rows = conn.execute(
            """
            SELECT ticker, source, endpoint, raw_field, raw_value, fiscal_year, status, sec_concept, unit, filed
            FROM api_cache WHERE ticker = ? ORDER BY id DESC LIMIT ?
            """,
            (ticker.upper().strip(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT ticker, source, endpoint, raw_field, raw_value, fiscal_year, status, sec_concept, unit, filed
            FROM api_cache ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    conn.close()
    return rows


def list_market_data(ticker: Optional[str] = None):
    conn = get_connection()
    if ticker:
        rows = conn.execute("SELECT * FROM market_data WHERE ticker = ?", (ticker.upper().strip(),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM market_data ORDER BY ticker").fetchall()
    conn.close()
    return rows


def list_model_readiness(ticker: Optional[str] = None):
    conn = get_connection()
    if ticker:
        rows = conn.execute("SELECT * FROM model_readiness WHERE ticker = ?", (ticker.upper().strip(),)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM model_readiness ORDER BY ticker").fetchall()
    conn.close()
    return rows
