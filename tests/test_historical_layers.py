import datetime as dt
import tempfile
import unittest
from pathlib import Path

from app.db import database
from app.services.historical_data_service import rebuild_historical_fundamentals_for_ticker
from app.services.price_history_service import recalculate_price_metrics_for_ticker


def api_row(ticker: str, field: str, value, fiscal_year: int) -> dict:
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


class HistoricalLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "test_tech_screener.db"
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def test_rebuild_historical_fundamentals_rolls_up_sec_annual_rows(self) -> None:
        database.add_ticker("TST", "Test Corp", "Testing", "Testing", "")
        rows = []
        for fiscal_year, revenue, shares in [(2023, 100.0, 100.0), (2024, 120.0, 120.0)]:
            rows.extend([
                api_row("TST", "revenue", revenue, fiscal_year),
                api_row("TST", "gross_profit", revenue * 0.5, fiscal_year),
                api_row("TST", "operating_income", revenue * 0.2, fiscal_year),
                api_row("TST", "net_income", revenue * 0.1, fiscal_year),
                api_row("TST", "operating_cash_flow", 30.0, fiscal_year),
                api_row("TST", "capital_expenditures", -10.0, fiscal_year),
                api_row("TST", "cash_and_equivalents", 50.0, fiscal_year),
                api_row("TST", "current_assets", 50.0, fiscal_year),
                api_row("TST", "current_liabilities", 25.0, fiscal_year),
                api_row("TST", "debt_current", 5.0, fiscal_year),
                api_row("TST", "debt_noncurrent", 15.0, fiscal_year),
                api_row("TST", "total_equity", 80.0, fiscal_year),
                api_row("TST", "shares_diluted", shares, fiscal_year),
            ])
        database.insert_api_cache_rows(rows)

        self.assertEqual(rebuild_historical_fundamentals_for_ticker("TST"), 2)
        history = database.list_historical_fundamentals("TST")
        latest = history[0]

        self.assertEqual(latest["fiscal_year"], 2024)
        self.assertAlmostEqual(latest["fcf_raw"], 20.0)
        self.assertAlmostEqual(latest["debt_raw"], 20.0)
        self.assertAlmostEqual(latest["current_ratio"], 2.0)
        self.assertAlmostEqual(latest["revenue_growth_yoy"], 0.2)
        self.assertAlmostEqual(latest["dilution_yoy"], 0.2)

    def test_recalculate_price_metrics_from_daily_history(self) -> None:
        database.add_ticker("TST", "Test Corp", "Testing", "Testing", "")
        start = dt.date(2024, 1, 1)
        price_rows = []
        for day in range(400):
            trade_date = start + dt.timedelta(days=day)
            close = 100.0 + (day * 0.1)
            price_rows.append({
                "ticker": "TST",
                "trade_date": trade_date.isoformat(),
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "adjusted_close": close,
                "volume": 1_000_000 + day,
                "source": "FINNHUB",
            })
        database.insert_price_history_rows(price_rows)

        self.assertEqual(recalculate_price_metrics_for_ticker("TST"), 1)
        metrics = database.list_price_metrics("TST")[0]

        self.assertEqual(metrics["last_trade_date"], "2025-02-03")
        self.assertAlmostEqual(metrics["last_close"], 139.9)
        self.assertTrue(metrics["momentum_flag"].startswith("GREEN"))
        self.assertIsNotNone(metrics["return_1y"])
        self.assertIsNotNone(metrics["volatility_90d"])


if __name__ == "__main__":
    unittest.main()
