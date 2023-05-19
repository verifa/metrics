"""Notion related functions and classes"""
import json
import logging
import os
import sys
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests


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

    def fetch_data(self, database_id) -> requests.Response:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        response = requests.post(url, headers={"Authorization": f"Bearer {self.token}", "Notion-Version": "2022-06-28"})
        return response


class WorkingHours(Notion):
    data: pd.DataFrame

    def __init__(self, token: Optional[str] = None, database_id: str = "") -> None:
        super().__init__(token, database_id)

    def get_workinghours(self) -> None:
        result_dict = self.fetch_data(self.database_id).json()
        data = pd.DataFrame(columns=["User", "Daily", "Delta", "Start", "Stop"])

        for item in result_dict["results"]:
            user = item["properties"]["User"]["title"][0]["plain_text"]
            daily = item["properties"]["Daily"]["number"]
            delta = item["properties"]["Delta"]["number"]
            start = item["properties"]["Start"]["rich_text"][0]["plain_text"]
            stop = item["properties"]["Stop"]["rich_text"][0]["plain_text"]

            data.loc[-1] = [user, daily, delta, start, stop]
            data.index = data.index + 1

        self.data = data.sort_values(by=["User"])


class Financials(Notion):
    data: pd.DataFrame

    def __init__(self, token: Optional[str] = None, database_id: str = "") -> None:
        super().__init__(token, database_id)

    def get_financials(self) -> None:
        result_dict = self.fetch_data(self.database_id).json()

        data = pd.DataFrame(columns=["Month", "Cost", "External_cost", "Real_income"])

        for item in result_dict["results"]:
            month = item["properties"]["Month"]["title"][0]["plain_text"]
            cost = item["properties"]["cost"]["formula"]["number"]
            extcost = item["properties"]["total-cost-b2b"]["formula"]["number"]
            income = item["properties"]["total-income"]["formula"]["number"]

            abcost = item["properties"]["AB-Cost"]["number"]
            oycost = item["properties"]["OY-Cost"]["number"]

            if oycost != None and abcost != None:
                data.loc[-1] = [month, cost, extcost, income]
                data.index = data.index + 1

        self.data = data.sort_values(by=["Month"])

        # Add 5 calculated cost trend
        average = sum(self.data["Cost"][-5:]) / 5
        extaverage = sum(self.data["External_cost"][-5:]) / 5
        y, m = list(map(int, self.data.tail(1)["Month"][self.data.index.max()].split("-")))
        for i in range(5):
            income = 0
            cost = average
            extcost = extaverage

            m = (m % 12) + 1
            y = y + 1 if m == 1 else y  # if dec -> jan then increase year
            m_ = f"0{m}" if m < 10 else str(m)
            month = f"{y}-{m_}"

            self.data.loc[-1] = [month, cost, extcost, income]
            self.data.index = self.data.index + 1

        logging.debug(f"Financial data\n{self.data}")


class OKR(Notion):
    data: pd.DataFrame

    def __init__(self, token: Optional[str] = None, database_id: str = "") -> None:
        super().__init__(token, database_id)

    def get_okr(self) -> None:
        result_dict = self.fetch_data(self.database_id).json()

        data = pd.DataFrame(
            columns=["title", "current_value", "target_value", "objective", "assignee", "period", "scope", "notes"]
        )

        for item in result_dict["results"]:
            if item["properties"]["Scope"]["select"]:
                if len(item["properties"]["Key Result"]["title"]):
                    title = item["properties"]["Key Result"]["title"][0]["text"]["content"]
                    current_value = item["properties"]["Current Value"]["number"]
                    target_value = item["properties"]["Target Value"]["number"]
                    objective = item["properties"]["Objective"]["select"]["name"]
                    noteslist = [i["plain_text"] for i in item["properties"]["Notes"]["rich_text"]]
                    notes = " ".join(noteslist)
                    assigneelist = sorted([person["name"] for person in item["properties"]["Assignee"]["people"]])
                    assignee = ", ".join(assigneelist)
                    period = sorted([p["name"] for p in item["properties"]["Period"]["multi_select"]])
                    scope = item["properties"]["Scope"]["select"]["name"]

                    data.loc[-1] = [title, current_value, target_value, objective, assignee, period, scope, notes]
                    data.index = data.index + 1
        self.data = data.sort_index()
        logging.debug(f"OKR data\n{self.data}")

    def get_figure_key_result(self, search_period=None) -> px.bar:
        keyresults = self.data[self.data["scope"] == "Company"]
        fig_title = "Key Results"

        if search_period:
            fig_title = f"{fig_title} {search_period}"
            keyresults = keyresults[keyresults["period"].isin([search_period])]

        logging.debug(f"Key Results\n{keyresults}")

        keyresults["Progress (%)"] = keyresults["current_value"] / keyresults["target_value"] * 100

        fig = px.bar(
            keyresults,
            x="Progress (%)",
            y="title",
            title=fig_title,
            height=100 + 50 * keyresults["title"].count(),
            orientation="h",
        )

        fig.update_layout(yaxis_title="")
        fig.update_xaxes(range=[0, 100])

        return fig

    def get_figure_initiatives(
        self, search_period=None, fnTableHeight=None, color_head="paleturquoise", color_cells="lavender"
    ) -> go.Figure:
        initiatives = self.data[self.data["scope"] == "Initiatives"]
        fig_title = "Initiatives"

        if search_period:
            fig_title = f"{fig_title} {search_period}"
            initiatives = initiatives[initiatives["period"].isin([search_period])]

        logging.debug(f"Initiatives\n{initiatives}")

        initiatives = initiatives.drop(
            ["current_value", "target_value", "objective", "scope", "period"], axis="columns"
        )

        fig = go.Figure(
            data=[
                go.Table(
                    columnwidth=[400, 400],
                    header=dict(values=list(initiatives.columns), fill_color=color_head, align="left"),
                    cells=dict(
                        values=[initiatives.title, initiatives.assignee, initiatives.notes],
                        fill_color=color_cells,
                        align="left",
                    ),
                )
            ]
        )
        fig.update_layout(title=fig_title)
        if fnTableHeight:
            fig.update_layout(height=fnTableHeight(initiatives, base_height=400))

        return fig
