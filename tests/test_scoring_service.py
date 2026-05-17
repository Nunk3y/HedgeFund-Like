import tempfile
import unittest
from pathlib import Path

from app.db import database
from app.services.scoring_service import list_score_details
from app.services.watchlist_service import list_master_watchlist, rank_label, risk_adjusted_score, score_data


class ScoringServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        database.DB_PATH = Path(self.tmp.name) / "test_tech_screener.db"
        database.init_db()

    def tearDown(self) -> None:
        database.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def insert_scored_ticker(self) -> None:
        database.add_ticker("TST", "Test Corp", "Testing", "Testing", "")
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
                "TST", "Test Corp", "Testing", "Testing",
                10.0, 1_000_000_000.0, 900_000_000.0,
                100_000_000.0, 100_000_000.0,
                200_000_000.0, 120_000_000.0, 50_000_000.0,
                60_000_000.0, -10_000_000.0, 50_000_000.0,
                200_000_000.0, 100_000_000.0, 2.0,
                5_000_000.0, 0.01, 0.03, "SEC EDGAR + FINNHUB",
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
                "TST", "Test Corp", "Testing", "Testing",
                "READY FOR PEER COMPARISON", "Review peer valuation", "None flagged", 1.0,
            ),
        )
        conn.commit()
        conn.close()

    def test_ready_for_peer_comparison_scores_as_complete_data(self) -> None:
        self.assertEqual(score_data("READY FOR PEER COMPARISON", "SEC EDGAR + FINNHUB"), 100)
        self.assertEqual(score_data("READY FOR DEEP-DIVE SCREENING - FCF NEGATIVE", "SEC EDGAR + FINNHUB"), 100)

    def test_risk_adjusted_score_caps_non_green_setups(self) -> None:
        self.assertEqual(risk_adjusted_score(86, "YELLOW - Watch / Needs Context"), 74)
        self.assertEqual(risk_adjusted_score(83, "RED - Skip / Too Weak"), 49)
        self.assertEqual(risk_adjusted_score(80, "GREEN - Deep Dive Candidate"), 80)
        self.assertEqual(rank_label(74, "YELLOW - Watch / Needs Context"), "B — Watch Closely")
        self.assertEqual(rank_label(49, "RED - Skip / Too Weak"), "D — Skip / Too Weak")

    def test_score_details_match_master_score_components(self) -> None:
        self.insert_scored_ticker()
        details = list_score_details("TST")
        master = list_master_watchlist()[0]

        self.assertEqual(len(details), 6)
        by_component = {row["Component"]: row for row in details}
        self.assertEqual(set(by_component), {"Data", "Quality", "Valuation", "Balance Sheet", "Dilution", "FCF"})
        self.assertEqual(by_component["Data"]["Component Score"], master["Data Score"])
        self.assertEqual(by_component["Quality"]["Component Score"], master["Quality Score"])
        self.assertEqual(by_component["Valuation"]["Component Score"], master["Valuation Score"])
        self.assertEqual(by_component["Balance Sheet"]["Component Score"], master["Balance Score"])
        self.assertEqual(by_component["Dilution"]["Component Score"], master["Dilution Score"])
        self.assertEqual(by_component["FCF"]["Component Score"], master["FCF Score"])
        self.assertTrue(all(row["Overall Score"] == master["Score"] for row in details))
        self.assertTrue(all(row["Raw Score"] == master["Raw Score"] for row in details))
        self.assertTrue(all(row["Inputs / Rationale"] for row in details))


if __name__ == "__main__":
    unittest.main()
