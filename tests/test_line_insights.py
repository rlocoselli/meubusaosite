import unittest
from unittest.mock import patch

import app as site


CITY = "Grenoble_France"


class LineInsightsTests(unittest.TestCase):
    def setUp(self):
        self.client = site.app.test_client()

    def test_city_and_line_show_insights_panel(self):
        with patch.object(site, "api_get", return_value=[]):
            city = self.client.get(f"/city/{CITY}")
            line = self.client.get(f"/city/{CITY}/line/12")
        self.assertIn(b'data-insights-city="Grenoble_France"', city.data)
        self.assertIn(b'data-insights-route="12"', line.data)
        self.assertIn(b"insights.js", city.data)

    def test_proxy_keeps_api_key_server_side_and_handles_missing_data(self):
        with patch.object(site, "api_get", return_value={"available":True, "items":[{"routeId":"12", "totalBoardings":7}]}) as upstream:
            response = self.client.get(f"/api/{CITY}/insights?route=12")
        self.assertEqual(response.get_json()["items"][0]["totalBoardings"], 7)
        self.assertEqual(upstream.call_args.args[0], f"insights/lines/{CITY}")
        self.assertEqual(upstream.call_args.kwargs["params"], {"routeId":"12"})
        with patch.object(site, "api_get", return_value=None):
            self.assertFalse(self.client.get(f"/api/{CITY}/insights").get_json()["available"])
            self.assertEqual(self.client.get(f"/api/{CITY}/realtime-status").get_json()["status"], "error")


if __name__ == "__main__":
    unittest.main()
