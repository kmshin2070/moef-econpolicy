import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sheet_layout  # noqa: E402


class TestColumnLetter(unittest.TestCase):
    def test_first_26(self):
        self.assertEqual(sheet_layout.column_letter(1), "A")
        self.assertEqual(sheet_layout.column_letter(2), "B")
        self.assertEqual(sheet_layout.column_letter(26), "Z")

    def test_beyond_26(self):
        self.assertEqual(sheet_layout.column_letter(27), "AA")
        self.assertEqual(sheet_layout.column_letter(28), "AB")
        self.assertEqual(sheet_layout.column_letter(52), "AZ")
        self.assertEqual(sheet_layout.column_letter(53), "BA")
        self.assertEqual(sheet_layout.column_letter(702), "ZZ")
        self.assertEqual(sheet_layout.column_letter(703), "AAA")

    def test_120_plus_1_label_column_range(self):
        # monthly tabs need up to 120 data columns + 1 label column (A);
        # data columns run B..DA (121 total => index 122 in 1-based incl A)
        self.assertEqual(sheet_layout.column_letter(121), "DQ")

    def test_invalid_index_raises(self):
        with self.assertRaises(ValueError):
            sheet_layout.column_letter(0)
        with self.assertRaises(ValueError):
            sheet_layout.column_letter(-5)


class TestResolveTabGrain(unittest.TestCase):
    def test_mixed_monthly_quarterly(self):
        indicators = [
            {"frequency": "monthly"},
            {"frequency": "monthly"},
            {"frequency": "quarterly"},
        ]
        self.assertEqual(sheet_layout.resolve_tab_grain(indicators), "monthly")

    def test_quarterly_and_annual(self):
        indicators = [{"frequency": "annual"}, {"frequency": "quarterly"}]
        self.assertEqual(sheet_layout.resolve_tab_grain(indicators), "quarterly")

    def test_all_annual(self):
        indicators = [{"frequency": "annual"}]
        self.assertEqual(sheet_layout.resolve_tab_grain(indicators), "annual")


class TestFormatPeriod(unittest.TestCase):
    def test_monthly_from_tuple(self):
        self.assertEqual(sheet_layout.format_period((2024, 6), "monthly"), "2024-06")

    def test_quarterly_from_tuple(self):
        self.assertEqual(sheet_layout.format_period((2024, 2), "quarterly"), "2024Q1")
        self.assertEqual(sheet_layout.format_period((2024, 4), "quarterly"), "2024Q2")

    def test_annual_from_int(self):
        self.assertEqual(sheet_layout.format_period(2024, "annual"), "2024")


class TestMapToGrainColumn(unittest.TestCase):
    def test_quarter_to_monthly_maps_to_last_month(self):
        self.assertEqual(
            sheet_layout.map_to_grain_column("2024Q1", "quarterly", "monthly"), "2024-03"
        )
        self.assertEqual(
            sheet_layout.map_to_grain_column("2024Q4", "quarterly", "monthly"), "2024-12"
        )

    def test_year_to_monthly_maps_to_december(self):
        self.assertEqual(
            sheet_layout.map_to_grain_column("2024", "annual", "monthly"), "2024-12"
        )

    def test_same_frequency_is_identity(self):
        self.assertEqual(
            sheet_layout.map_to_grain_column("2024-05", "monthly", "monthly"), "2024-05"
        )

    def test_industrial_activity_trends_case(self):
        # category "Industrial Activity Trends": 2 monthly + 1 quarterly
        # indicator (ind_prod_qoq_from_quarterly) -> tab grain monthly.
        indicators = [
            {"id": "ind_prod_mom", "frequency": "monthly"},
            {"id": "ind_prod_qoq_from_monthly", "frequency": "monthly"},
            {"id": "ind_prod_qoq_from_quarterly", "frequency": "quarterly"},
        ]
        grain = sheet_layout.resolve_tab_grain(indicators)
        self.assertEqual(grain, "monthly")
        mapped = sheet_layout.map_to_grain_column("2024Q1", "quarterly", grain)
        self.assertEqual(mapped, "2024-03")


class TestSlidingWindow(unittest.TestCase):
    def test_drops_oldest_beyond_retention(self):
        periods = ["2020-01", "2020-02", "2020-03", "2020-04", "2020-05"]
        kept, dropped = sheet_layout.sliding_window(
            periods, "monthly", {"monthly": 3}
        )
        self.assertEqual(kept, ["2020-03", "2020-04", "2020-05"])
        self.assertEqual(dropped, ["2020-01", "2020-02"])

    def test_no_drop_when_within_retention(self):
        periods = ["2020-01", "2020-02"]
        kept, dropped = sheet_layout.sliding_window(
            periods, "monthly", {"monthly": 120}
        )
        self.assertEqual(kept, ["2020-01", "2020-02"])
        self.assertEqual(dropped, [])

    def test_quarterly_sort_and_retain(self):
        periods = ["2019Q4", "2020Q1", "2019Q1", "2020Q2"]
        kept, dropped = sheet_layout.sliding_window(
            periods, "quarterly", {"quarterly": 2}
        )
        self.assertEqual(kept, ["2020Q1", "2020Q2"])
        self.assertEqual(sorted(dropped), ["2019Q1", "2019Q4"])

    def test_deduplicates(self):
        periods = ["2020-01", "2020-01", "2020-02"]
        kept, dropped = sheet_layout.sliding_window(
            periods, "monthly", {"monthly": 120}
        )
        self.assertEqual(kept, ["2020-01", "2020-02"])
        self.assertEqual(dropped, [])


class TestDiffRows(unittest.TestCase):
    def test_new_row_all_new(self):
        fresh = [{"period": "2024-01", "value": 1.0}, {"period": "2024-02", "value": 2.0}]
        result = sheet_layout.diff_rows(None, fresh)
        self.assertEqual(result, fresh)

    def test_existing_row_only_changed_or_new(self):
        current = {
            "row": 2,
            "values": {"2024-01": 1.0, "2024-02": 2.0},
        }
        fresh = [
            {"period": "2024-01", "value": 1.0},  # unchanged -> excluded
            {"period": "2024-02", "value": 2.5},  # changed -> included
            {"period": "2024-03", "value": 3.0},  # new -> included
        ]
        result = sheet_layout.diff_rows(current, fresh)
        self.assertEqual(
            result,
            [
                {"period": "2024-02", "value": 2.5},
                {"period": "2024-03", "value": 3.0},
            ],
        )

    def test_float_tolerance(self):
        current = {"row": 2, "values": {"2024-01": 1.0000000001}}
        fresh = [{"period": "2024-01", "value": 1.0000000002}]
        result = sheet_layout.diff_rows(current, fresh, tolerance=1e-9)
        self.assertEqual(result, [])  # within tolerance -> no-op

        fresh_changed = [{"period": "2024-01", "value": 1.1}]
        result_changed = sheet_layout.diff_rows(current, fresh_changed, tolerance=1e-9)
        self.assertEqual(result_changed, [{"period": "2024-01", "value": 1.1}])


class TestAssignRow(unittest.TestCase):
    def test_reuses_existing_row(self):
        category_state = {"rows": {"gdp_yoy": {"row": 5, "values": {}}}}
        row = sheet_layout.assign_row(category_state, "gdp_yoy", existing_max_row=5, header_row=1)
        self.assertEqual(row, 5)

    def test_new_indicator_gets_next_row(self):
        category_state = {"rows": {"gdp_yoy": {"row": 5, "values": {}}}}
        row = sheet_layout.assign_row(category_state, "gdp_qoq", existing_max_row=5, header_row=1)
        self.assertEqual(row, 6)

    def test_brand_new_category_uses_header_row(self):
        category_state = {"rows": {}}
        row = sheet_layout.assign_row(category_state, "gdp_yoy", existing_max_row=0, header_row=1)
        self.assertEqual(row, 2)

    def test_none_category_state(self):
        row = sheet_layout.assign_row(None, "gdp_yoy", existing_max_row=0, header_row=1)
        self.assertEqual(row, 2)


if __name__ == "__main__":
    unittest.main()
