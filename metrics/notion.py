"""Notion related functions and classes"""

import logging
import os
import sys
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

from metrics.tempo_config import EUR2SEK


class Notion:
    """
    I'M A DOCSTRING SHORT AND STOUT
    """

    token: str
    database_id: str

    def __init__(self, token: Optional[str] = None, database_id: str = "") -> None:
        token = token or os.environ.get("NOTION_KEY")
        if token is None:
            sys.exit("Notion token not provided or NOTION_KEY not set")
        self.token = token
        self.database_id = database_id

    def fetch_data(self, payload: dict[str, str] = {}) -> map:
        url = f"https://api.notion.com/v1/databases/{self.database_id}/query"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        json_data = response.json()
        # Recursive until all rows are fetched, only 100 rows max allowed
        if json_data["has_more"]:
            next_cur = json_data["next_cursor"]
            json_data["results"] += self.fetch_data({"start_cursor": next_cur})

        return json_data["results"]


class WorkingHours(Notion):
    "The class for working hour handling"
    data: pd.DataFrame

    def get_workinghours(self) -> None:
        result_dict = self.fetch_data()
        data = pd.DataFrame(columns=["User", "Daily", "Delta", "Start", "Stop"])

        for item in result_dict:
            user = item["properties"]["User"]["title"][0]["plain_text"]
            daily = item["properties"]["Daily"]["number"]
            delta = item["properties"]["Delta"]["number"]
            start = item["properties"]["Start"]["rich_text"][0]["plain_text"]
            stop = item["properties"]["Stop"]["rich_text"][0]["plain_text"]

            data.loc[-1] = [user, daily, delta, start, stop]
            data.index = data.index + 1

        self.data = data.sort_values(by=["User"])


class Allocations(Notion):
    "The class for allocations"
    data: pd.DataFrame

    def get_allocations(self) -> None:
        result_dict = self.fetch_data()
        data = pd.DataFrame(columns=["User", "Allocation", "Start", "Stop", "Unconfirmed", "JiraID"])

        for item in result_dict:
            user = item["properties"]["Assign"]["people"][0]["name"]
            allocation = item["properties"]["Allocation"]["number"]
            start = item["properties"]["Date"]["date"]["start"]
            stop = item["properties"]["Date"]["date"]["end"]
            unconfirmed = item["properties"]["Unconfirmed"]["checkbox"]
            jiratext = item["properties"]["Task ID"]["rich_text"]
            if jiratext == []:
                jiraid = "?"
            else:
                jiraid = jiratext[0]["plain_text"]

            data.loc[-1] = [user, allocation, start, stop, unconfirmed, jiraid]
            data.index = data.index + 1

        self.data = data.sort_values(by=["User"])


class Crew(Notion):
    "The class for crew data"
    data: pd.DataFrame

    def get_crew(self) -> None:
        result_dict = self.fetch_data()
        data = pd.DataFrame(columns=["User", "Role", "Hours", "Total cost", "UserId"])
        for item in result_dict:
            user = item["properties"]["Person"]["people"][0]["name"]
            jira_id = item["properties"]["JIRA ID"]["rich_text"][0]["plain_text"]
            role = item["properties"]["Role"]["select"]["name"]
            currency = item["properties"]["Currency"]["select"]["name"]
            cost = item["properties"]["Total Cost"]["number"] / (EUR2SEK if currency == "SEK" else 1)
            hours = item["properties"]["Consulting Hours"]["number"]
            data.loc[-1] = [user, role, hours, cost, jira_id]
            data.index = data.index + 1

        self.data = data.sort_values(by=["User"])


class Financials(Notion):
    "The class for finance data"
    data: pd.DataFrame

    def get_financials(self) -> None:
        result_dict = self.fetch_data()

        data = pd.DataFrame(columns=["Month", "External_cost", "Real_income", "Starting_amount"])

        for item in result_dict:
            month = item["properties"]["Month"]["title"][0]["plain_text"]
            extcost = item["properties"]["external-cost"]["formula"]["number"]
            income = item["properties"]["real-income"]["formula"]["number"]

            sekstart = item["properties"]["SEK Start"]["number"]
            eurstart = item["properties"]["EUR Start"]["number"]
            start = 0
            if sekstart is not None:
                start += sekstart / EUR2SEK
            if eurstart is not None:
                start += eurstart

            abcost = item["properties"]["AB-Cost"]["number"]
            oycost = item["properties"]["OY-Cost"]["number"]

            if oycost is not None and abcost is not None:
                data.loc[-1] = [month, extcost, income, start]
                data.index = data.index + 1

        self.data = data.sort_values(by=["Month"])

        current_finances = 0
        for i in range(len(self.data) - 1, 0, -1):
            start = self.data["Starting_amount"][i]
            current_finances += self.data["Real_income"][i] - self.data["External_cost"][i] + start
            if start != 0:
                break

        # Add 5 projected cost entries based on recent average
        extaverage = (
            sum(self.data["External_cost"][-3:])
            + sum(self.data["External_cost"][-2:])
            + sum(self.data["External_cost"][-1:])
        ) / 6
        y, m = list(map(int, self.data.tail(1)["Month"][self.data.index.max()].split("-")))
        for i in range(5):
            extcost = extaverage

            m = (m % 12) + 1
            y = y + 1 if m == 1 else y  # if dec -> jan then increase year
            m_ = f"0{m}" if m < 10 else str(m)
            month = f"{y}-{m_}"

            self.data.loc[-1] = [month, extcost, 0, current_finances]
            self.data.index = self.data.index + 1
            current_finances = 0

        logging.debug("Financial data\n%s", self.data)


class RatesCurrency(Notion):
    "The class for Currency conversion data"
    data: pd.DataFrame

    def get_rates(self) -> None:
        result_dict = self.fetch_data()
        self.data = pd.DataFrame(columns=["SEK2EUR"])
        for item in result_dict:
            sek2euro = item["properties"]["SEK2EUR"]["number"]
            self.data.loc[-1] = [sek2euro]
            self.data.index += 1


class RatesDefault(Notion):
    "The class for Default Rates data"
    data: pd.DataFrame

    def get_rates(self) -> None:
        result_dict = self.fetch_data()
        self.data = pd.DataFrame(columns=["Key", "Rate", "Currency"])
        for item in result_dict:
            key = item["properties"]["Key"]["title"][0]["plain_text"]
            rate = item["properties"]["Rate"]["number"]
            currency = item["properties"]["Currency"]["select"]["name"]
            self.data.loc[-1] = [key, rate, currency]
            self.data.index += 1


class RatesExceptions(Notion):
    "The class for Exceptional Rates data"
    data: pd.DataFrame

    def get_rates(self) -> None:
        result_dict = self.fetch_data()
        self.data = pd.DataFrame(columns=["Key", "Rate", "User"])
        for item in result_dict:
            key = item["properties"]["Key"]["select"]["name"]
            rate = item["properties"]["Rate"]["number"]
            user = item["properties"]["User"]["title"][0]["plain_text"]
            self.data.loc[-1] = [key, rate, user]
            self.data.index += 1


class RatesInternal(Notion):
    "The class for Exceptional Rates data"
    data: pd.DataFrame

    def get_rates(self) -> None:
        result_dict = self.fetch_data()
        self.data = pd.DataFrame(columns=["Key"])
        for item in result_dict:
            key = item["properties"]["Key"]["title"][0]["plain_text"]
            self.data.loc[-1] = [key]
            self.data.index += 1
