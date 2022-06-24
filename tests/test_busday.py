import unittest

import numpy


class TestBusday(unittest.TestCase):
    """some simple tests for numpy.busday"""

    def test_one_day_weekend(self):
        self.assertEqual(numpy.busday_count("2022-01-01", "2022-01-02", weekmask="1111100"), 0, "Should be 0")

    def test_one_day_week(self):
        self.assertEqual(numpy.busday_count("2022-01-03", "2022-01-04", weekmask="1111100"), 1, "Should be 1")

    def test_one_week(self):
        self.assertEqual(numpy.busday_count("2022-01-01", "2022-01-07", weekmask="1111100"), 4, "Should be 4")

    def test_two_weeks(self):
        self.assertEqual(numpy.busday_count("2022-01-01", "2022-01-14", weekmask="1111100"), 9, "Should be 9")


if __name__ == "__main__":
    unittest.main()
