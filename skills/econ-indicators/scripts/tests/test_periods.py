import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import periods  # noqa: E402


class TestFormatPeriod(unittest.TestCase):
    def test_monthly_from_tuple(self):
        self.assertEqual(periods.format_period((2024, 6), "monthly"), "2024-06")

    def test_quarterly_from_tuple(self):
        self.assertEqual(periods.format_period((2024, 2), "quarterly"), "2024Q1")
        self.assertEqual(periods.format_period((2024, 4), "quarterly"), "2024Q2")

    def test_annual_from_int(self):
        self.assertEqual(periods.format_period(2024, "annual"), "2024")

    def test_monthly_from_date_string(self):
        self.assertEqual(periods.format_period("2024-06-15", "monthly"), "2024-06")

    def test_monthly_requires_month(self):
        with self.assertRaises(ValueError):
            periods.format_period(2024, "monthly")

    def test_unknown_frequency_raises(self):
        with self.assertRaises(ValueError):
            periods.format_period((2024, 6), "weekly")


class TestSlidingWindow(unittest.TestCase):
    def test_drops_oldest_beyond_retention(self):
        all_periods = ["2020-01", "2020-02", "2020-03", "2020-04", "2020-05"]
        kept, dropped = periods.sliding_window(all_periods, "monthly", {"monthly": 3})
        self.assertEqual(kept, ["2020-03", "2020-04", "2020-05"])
        self.assertEqual(dropped, ["2020-01", "2020-02"])

    def test_no_drop_when_within_retention(self):
        all_periods = ["2020-01", "2020-02"]
        kept, dropped = periods.sliding_window(all_periods, "monthly", {"monthly": 120})
        self.assertEqual(kept, ["2020-01", "2020-02"])
        self.assertEqual(dropped, [])

    def test_quarterly_sort_and_retain(self):
        all_periods = ["2019Q4", "2020Q1", "2019Q1", "2020Q2"]
        kept, dropped = periods.sliding_window(all_periods, "quarterly", {"quarterly": 2})
        self.assertEqual(kept, ["2020Q1", "2020Q2"])
        self.assertEqual(sorted(dropped), ["2019Q1", "2019Q4"])

    def test_annual_sort_and_retain(self):
        all_periods = ["2018", "2022", "2019", "2021", "2020"]
        kept, dropped = periods.sliding_window(all_periods, "annual", {"annual": 3})
        self.assertEqual(kept, ["2020", "2021", "2022"])
        self.assertEqual(sorted(dropped), ["2018", "2019"])

    def test_deduplicates(self):
        all_periods = ["2020-01", "2020-01", "2020-02"]
        kept, dropped = periods.sliding_window(all_periods, "monthly", {"monthly": 120})
        self.assertEqual(kept, ["2020-01", "2020-02"])
        self.assertEqual(dropped, [])


if __name__ == "__main__":
    unittest.main()
