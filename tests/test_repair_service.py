import datetime as dt
import tempfile
import unittest
from pathlib import Path

from app.db import database
from app.services.repair_service import repair_all_missing_data


def sec_history_row(ticker: str, field: str, value, fiscal_year: int) -> dict:
    return {
        "Ticker": ticker,
        "Timestamp": "2026-01-01T00:00:00+00:00",
        "Source": "SEC EDGAR",
        "Endpoint / Metric": "companyfacts_annual_history",
        "Raw Field": f"{field}_history",
        "Raw Value": value,
        "Period": "FY",
        "Fiscal Year": str(fiscal_year),
        "Status": "OK",
        "Error Message": "",
        "Notes": "",
        "CIK": "1",
        "SEC Concept": field,
        "Unit": "USD",
        "Form": "10-K",
        "Filed": f"{fiscal_year + 1}-02-15",
        "Period Start": f"{fiscal_year}-01-01",
        "Period End": f"{fiscal_year}-12-31",
        "Frame": f"CY{fiscal_year}",
        "Accession": "",
    }


class RepairServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "test_tech_screener.db"
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def test_repair_rebuilds_cached_history_and_existing_price_metrics(self) -> None:
        database.add_ticker("TST", "Test Corp", "Testing", "Testing", "")
        sec_rows = []
        for fiscal_year, revenue in [(2022, 80.0), (2023, 100.0), (2024, 125.0)]:
            sec_rows.extend([
                sec_history_row("TST", "revenue", revenue, fiscal_year),
                sec_history_row("TST", "gross_profit", revenue * 0.55, fiscal_year),
                sec_history_row("TST", "operating_income", revenue * 0.25, fiscal_year),
                sec_history_row("TST", "net_income", revenue * 0.15, fiscal_year),
                sec_history_row("TST", "operating_cash_flow", 35.0, fiscal_year),
                sec_history_row("TST", "capital_expenditures", -10.0, fiscal_year),
                sec_history_row("TST", "cash_and_equivalents", 70.0, fiscal_year),
                sec_history_row("TST", "current_assets", 90.0, fiscal_year),
                sec_history_row("TST", "current_liabilities", 30.0, fiscal_year),
                sec_history_row("TST", "debt_current", 8.0, fiscal_year),
                sec_history_row("TST", "debt_noncurrent", 12.0, fiscal_year),
                sec_history_row("TST", "total_equity", 120.0, fiscal_year),
                sec_history_row("TST", "shares_diluted", 100.0 + fiscal_year - 2022, fiscal_year),
            ])
        database.insert_api_cache_rows(sec_rows)

        start = dt.date(2024, 1, 1)
        price_rows = []
        for day in range(370):
            trade_date = start + dt.timedelta(days=day)
            close = 50.0 + day * 0.05
            price_rows.append({
                "ticker": "TST",
                "trade_date": trade_date.isoformat(),
                "open": close - 0.25,
                "high": close + 0.75,
                "low": close - 0.75,
                "close": close,
                "adjusted_close": close,
                "volume": 500_000 + day,
                "source": "FINNHUB",
            })
        database.insert_price_history_rows(price_rows)

        results = repair_all_missing_data(finnhub_key="")

        self.assertEqual([result.ticker for result in results], ["TST"])
        self.assertEqual(results[0].history_years, 3)
        self.assertEqual(results[0].price_rows, 0)
        self.assertTrue(results[0].normalized)
        self.assertTrue(results[0].readiness)
        self.assertEqual(results[0].warning, "")
        self.assertEqual(len(database.list_historical_fundamentals("TST")), 3)
        self.assertEqual(len(database.list_price_metrics("TST")), 1)
        self.assertEqual(len(database.list_market_data("TST")), 1)
        self.assertEqual(len(database.list_model_readiness("TST")), 1)


if __name__ == "__main__":
    unittest.main()
