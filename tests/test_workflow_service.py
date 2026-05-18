import tempfile
import unittest
from pathlib import Path

from app.db import database
from app.services.peer_service import list_peer_comparison
from app.services.watchlist_service import list_master_watchlist, score_data


class WorkflowServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "test_tech_screener.db"
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def insert_ticker(
        self,
        ticker: str,
        *,
        peer_group: str = "Testing",
        fcf: float = 50_000_000.0,
        cash: float = 200_000_000.0,
        debt: float = 100_000_000.0,
        dilution_1y: float = 0.01,
        dilution_3y: float = 0.03,
    ) -> None:
        database.add_ticker(ticker, f"{ticker} Corp", peer_group, peer_group, "")
        conn = database.get_connection()
        conn.execute(
            """
            INSERT INTO market_data (
                ticker, company, category, peer_group,
                price_per_share, market_cap_raw, enterprise_value_raw,
                shares_out_raw, diluted_shares_raw,
                revenue_raw, gross_profit_raw, operating_income_raw,
                operating_cash_flow_raw, capex_raw, fcf_raw,
                cash_raw, debt_raw, current_ratio,
                sbc_raw, dilution_1y, dilution_3y, source_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker, f"{ticker} Corp", peer_group, peer_group,
                10.0, 1_000_000_000.0, 900_000_000.0,
                100_000_000.0, 100_000_000.0,
                200_000_000.0, 120_000_000.0, 50_000_000.0,
                60_000_000.0, -10_000_000.0, fcf,
                cash, debt, 2.0,
                5_000_000.0, dilution_1y, dilution_3y, "SEC EDGAR + FINNHUB",
            ),
        )
        conn.execute(
            """
            INSERT INTO model_readiness (
                ticker, company, category, peer_group,
                readiness, next_action, missing_weak_areas, core_data_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticker, f"{ticker} Corp", peer_group, peer_group,
                "READY FOR PEER COMPARISON", "Review peer valuation", "None flagged", 1.0,
            ),
        )
        conn.commit()
        conn.close()

    def test_ready_for_peer_comparison_scores_as_complete_data(self) -> None:
        self.assertEqual(score_data("READY FOR PEER COMPARISON", "SEC EDGAR + FINNHUB"), 100)
        self.assertEqual(score_data("READY FOR DEEP-DIVE SCREENING - FCF NEGATIVE", "SEC EDGAR + FINNHUB"), 100)

    def test_master_watchlist_uses_workflow_fields(self) -> None:
        self.insert_ticker("TST")
        row = list_master_watchlist()[0]

        self.assertEqual(row["Review Status"], "GREEN — Ready For Peer Gate")
        self.assertEqual(row["Red Flags"], "None flagged")
        self.assertEqual(row["Watch Items"], "None flagged")
        self.assertIn("Peer Gate", row["Action"])
        self.assertIn("Standalone Business Flag", row)
        self.assertIn("Standalone Valuation Flag", row)
        self.assertIn("Standalone Balance Flag", row)
        self.assertIn("Standalone Dilution Flag", row)

    def test_master_watchlist_surfaces_standalone_red_flags(self) -> None:
        self.insert_ticker("RISK", fcf=-20_000_000.0, cash=5_000_000.0, debt=50_000_000.0, dilution_1y=0.30, dilution_3y=0.80)
        row = list_master_watchlist()[0]

        self.assertTrue(row["Review Status"].startswith("RED"))
        self.assertIn("FCF Negative", row["Red Flags"])
        self.assertIn("Weak Runway", row["Red Flags"])
        self.assertIn("High Dilution", row["Red Flags"])

    def test_peer_comparison_includes_relative_dilution(self) -> None:
        conn = database.get_connection()
        for ticker, dilution_3y in [("TST", 0.02), ("PEER", 0.10)]:
            conn.execute(
                """
                INSERT INTO market_data (
                    ticker, company, category, peer_group,
                    market_cap_raw, enterprise_value_raw, revenue_raw,
                    gross_profit_raw, operating_income_raw, fcf_raw,
                    current_ratio, dilution_1y, dilution_3y
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticker, f"{ticker} Corp", "Testing", "Testing",
                    1_000_000_000.0, 900_000_000.0, 200_000_000.0,
                    120_000_000.0, 50_000_000.0, 50_000_000.0,
                    2.0, dilution_3y / 3, dilution_3y,
                ),
            )
        conn.commit()
        conn.close()

        rows = {row["Ticker"]: row for row in list_peer_comparison()}

        self.assertIn("Relative Dilution Flag", rows["TST"])
        self.assertEqual(rows["TST"]["Relative Dilution Flag"], "GREEN — Low Dilution vs Peers")
        self.assertEqual(rows["PEER"]["Relative Dilution Flag"], "RED — High Dilution vs Peers")
        self.assertEqual(rows["TST"]["Peer Median Dilution 3Y"], "6.00%")


if __name__ == "__main__":
    unittest.main()
