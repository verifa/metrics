"""
Unit tests for the notion class
"""

import os
import unittest

from metrics import notion


class TestNotion(unittest.TestCase):
    "the unit tests"

    def test_fetch_data(self):
        os.environ.pop("NOTION_KEY", None)

        with self.assertRaises(SystemExit) as cm:
            notion.OKR().get_okr()

        self.assertEqual(cm.exception.code, "Notion token not provided or NOTION_KEY not set")


if __name__ == "__main__":
    unittest.main()
