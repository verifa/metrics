import importlib.util
import sys
import unittest


def load_module(file_name, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


load_module("routes/date_utils.py", "date_utils")
from date_utils import *


class TestWeekdays(unittest.TestCase):
    """some simple tests for the weekdays() function"""

    def test_one_day(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-02"), 0, "Should be 0")

    def test_two_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-03"), 1, "Should be 1")

    def test_three_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-04"), 2, "Should be 2")

    def test_four_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-05"), 3, "Should be 3")

    def test_five_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-06"), 4, "Should be 4")

    def test_six_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-07"), 5, "Should be 5")

    def test_one_week(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-08"), 5, "Should be 5")

    def test_eight_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-09"), 5, "Should be 5")

    def test_nine_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-10"), 6, "Should be 6")

    def test_ten_days(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-11"), 7, "Should be 7")

    def test_two_weeks(self):
        self.assertEqual(weekdays("2022-01-01", "2022-01-14"), 10, "Should be 10")


class TestLookAhead(unittest.TestCase):
    "tests for the lookAhead() function"

    def test_increament_one(self):
        self.assertEqual(str(lookAhead(1, "2022-01-01").date()), "2022-01-02", "Should be 2022-01-02")


if __name__ == "__main__":
    unittest.main()
