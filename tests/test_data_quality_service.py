import tempfile
import unittest
from pathlib import Path

from app.db import database
from app.services.data_quality_service import list_data_quality, list_data_quality_summary


def cache_row(ticker: str, source: str, field: str, value) -> dict:
    return {
        "Ticker": ticker,
        "Timestamp": "2026-01-01T00:00:00+00:00",
        "Source": source,
        "Endpoint / Metric": "test",
        "Raw Field": field,
        "Raw Value": value,
        "Period": "",
        "Fiscal Year": "",
        "Status": "OK",
        "Error Message": "",
        "Notes": "",
        "CIK": "",
        "SEC Concept": "",
        "Unit": "",
        "Form": "",
        "Filed": "",
        "Period Start": "",
        "Period End": "",
        "Frame": "",
        "Accession": "",
    }


class DataQualityServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "test_tech_screener.db"
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def test_data_quality_marks_complete_partial_and_missing_fields(self) -> None:
        database.add_ticker("TST", "Test Corp", "Testing", "Testing", "")
        database.insert_api_cache_rows([
            cache_row("TST", "SEC EDGAR", "revenue", 100.0),
            cache_row("TST", "FINNHUB", "c", 10.0),
        ], replace_source_for_ticker=False)
        conn = database.get_connection()
        conn.execute(
            """
            INSERT INTO market_data (
                ticker, company, category, peer_group,
                price_per_share, market_cap_raw, shares_out_raw,
                revenue_raw, gross_profit_raw, fcf_raw,
                cash_raw, debt_raw, current_ratio,
                dilution_1y, source_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "TST", "Test Corp", "Testing", "Testing",
                10.0, 1_000_000_000.0, 100_000_000.0,
                200_000_000.0, 100_000_000.0, 25_000_000.0,
                50_000_000.0, 10_000_000.0, 2.0,
                0.01, "SEC EDGAR + FINNHUB",
            ),
        )
        conn.commit()
        conn.close()

        rows = list_data_quality("TST")
        by_field = {row["Field"]: row for row in rows}

        self.assertEqual(len(rows), 14)
        self.assertTrue(by_field["Price"]["Quality Status"].startswith("GREEN"))
        self.assertTrue(by_field["Revenue"]["Quality Status"].startswith("GREEN"))
        self.assertTrue(by_field["Dilution"]["Quality Status"].startswith("YELLOW"))
        self.assertTrue(by_field["EBITDA"]["Quality Status"].startswith("GRAY"))
        self.assertTrue(by_field["Historical Fundamentals"]["Quality Status"].startswith("GRAY"))

        summary = list_data_quality_summary("TST")[0]
        self.assertEqual(summary["Ticker"], "TST")
        self.assertTrue(summary["Data Quality Flag"].startswith("YELLOW"))
        self.assertGreater(int(summary["Complete Fields"]), 0)
        self.assertGreater(int(summary["Missing / Red"]), 0)
        self.assertIn("EBITDA", summary["Weakest Fields"])


if __name__ == "__main__":
    unittest.main()
