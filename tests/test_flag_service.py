import unittest

from app.services.flag_service import flag_data_confidence, flag_valuation


class FlagServiceTests(unittest.TestCase):
    def test_not_screen_ready_counts_as_insufficient_data(self) -> None:
        self.assertTrue(
            flag_data_confidence("NOT SCREEN READY", "Missing: Price").startswith("GRAY")
        )

    def test_pre_revenue_readiness_uses_speculative_valuation_flag(self) -> None:
        valuation = flag_valuation(None, None, 0, None, None, "PARTIAL COMPARISON ONLY - PRE-REVENUE")

        self.assertTrue(valuation.startswith("PURPLE"))


if __name__ == "__main__":
    unittest.main()
