import unittest

from app.services.price_data_service import parse_yahoo_chart_rows, yahoo_symbol


class PriceDataServiceTests(unittest.TestCase):
    def test_yahoo_symbol_converts_dotted_symbols(self) -> None:
        self.assertEqual(yahoo_symbol("brk.b"), "BRK-B")

    def test_parse_yahoo_chart_rows_maps_ohlcv_and_adjusted_close(self) -> None:
        payload = {
            "chart": {
                "result": [{
                    "timestamp": [1735689600, 1735776000],
                    "indicators": {
                        "quote": [{
                            "open": [10.0, 10.5],
                            "high": [11.0, 11.5],
                            "low": [9.5, 10.0],
                            "close": [10.75, 11.25],
                            "volume": [1000, 1200],
                        }],
                        "adjclose": [{"adjclose": [10.7, 11.2]}],
                    },
                }],
                "error": None,
            }
        }

        rows = parse_yahoo_chart_rows("TST", payload)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["ticker"], "TST")
        self.assertEqual(rows[0]["trade_date"], "2025-01-01")
        self.assertEqual(rows[0]["close"], 10.75)
        self.assertEqual(rows[0]["adjusted_close"], 10.7)
        self.assertEqual(rows[0]["source"], "YAHOO_CHART")


if __name__ == "__main__":
    unittest.main()
