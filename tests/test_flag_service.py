import unittest

from app.services.flag_service import flag_data_confidence, flag_overall, flag_valuation


class FlagServiceTests(unittest.TestCase):
    def test_not_screen_ready_counts_as_insufficient_data(self) -> None:
        self.assertTrue(
            flag_data_confidence("NOT SCREEN READY", "Missing: Price").startswith("GRAY")
        )

    def test_pre_revenue_readiness_uses_speculative_flags(self) -> None:
        valuation = flag_valuation(None, None, 0, None, None, "PARTIAL COMPARISON ONLY - PRE-REVENUE")
        overall = flag_overall(
            "PARTIAL COMPARISON ONLY - PRE-REVENUE",
            "GRAY - Core Data Missing",
            valuation,
            "PURPLE - Pre-Revenue",
            "GREEN - Strong Runway",
            "GRAY - Missing Dilution",
            "Business realities: pre-revenue",
        )

        self.assertTrue(valuation.startswith("PURPLE"))
        self.assertTrue(overall.startswith("PURPLE"))


if __name__ == "__main__":
    unittest.main()
