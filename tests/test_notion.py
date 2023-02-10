import os
import unittest

import routes.notion as notion


class TestNotion(unittest.TestCase):
    def test_fetch_data(self):
        os.environ.pop("NOTION_KEY", None)

        with self.assertRaises(SystemExit) as cm:
            notion.OKR().get_okr()

        self.assertEqual(cm.exception.code, "Notion token not provided or NOTION_KEY not set")


if __name__ == "__main__":
    unittest.main()
