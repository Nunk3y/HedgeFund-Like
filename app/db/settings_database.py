import sqlite3
from pathlib import Path

SETTINGS_DB_PATH = Path("personal_settings.db")


def get_settings_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(SETTINGS_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def ensure_app_settings_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)


def get_setting(key: str, default: str = "") -> str:
    conn = get_settings_connection()
    ensure_app_settings_table(conn)
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row and row["value"] is not None else default


def set_setting(key: str, value: str) -> None:
    conn = get_settings_connection()
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
