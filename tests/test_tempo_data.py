import unittest

import pandas as pd

from metrics.constants import TEMPO_CONFIG_PATH
from metrics.tempo_data import TempoData


class TestTempoData(unittest.TestCase):

    tempo: TempoData = TempoData(TEMPO_CONFIG_PATH)

    def test_all_jira_issues(self):
        issues = self.tempo.allJiraIssues()
        self.assertGreater(len(issues), 400)

    def test_all_jira_users(self):
        users = self.tempo.allJiraUsers()
        self.assertGreater(len(users), 50)
