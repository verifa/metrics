"""
Checks for the Notion

"""

import unittest

import pandas as pd

# Constants
from metrics.constants import (
    NOTION_ALLOCATION_DATABASE_ID,
    NOTION_CREW_DATABASE_ID,
    NOTION_FINANCIAL_DATABASE_ID,
    NOTION_KEY,
    NOTION_RATES_DATABASE_ID,
    NOTION_WORKINGHOURS_DATABASE_ID,
)
from metrics.notion import Allocations, Crew, Financials, Rates, WorkingHours


class TestWorkHours(unittest.TestCase):

    def test_notion_working_hours(self):
        wh = WorkingHours(NOTION_KEY, NOTION_WORKINGHOURS_DATABASE_ID)
        wh.get_workinghours()
        self.assertEqual(wh.data["Daily"][0], 8)


class TestCrew(unittest.TestCase):

    def test_notion_crew(self):
        cr = Crew(NOTION_KEY, NOTION_CREW_DATABASE_ID)
        cr.get_crew()
        self.assertEqual(cr.data["Role"][0], "Consultant")


class TestFinancials(unittest.TestCase):

    def test_notion_financials(self):
        f = Financials(NOTION_KEY, NOTION_FINANCIAL_DATABASE_ID)
        f.get_financials()
        self.assertEqual(f.data["Month"][5], "2021-02")


class TestRates(unittest.TestCase):

    def test_rates(self):
        r = Rates(NOTION_KEY, NOTION_RATES_DATABASE_ID)
        r.get_rates()
        self.assertEqual("FAT-1", r.data.loc[0]["Key"])
