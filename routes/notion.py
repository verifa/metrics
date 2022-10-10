"""Notion related functions and classes"""
import json
import logging
import os
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests


class Notion:
    token: str

    def __init__(self, token: str = None) -> None:
        token = token or os.environ.get("NOTION_KEY")
        if token is None:
            sys.exit("Notion token not provided or NOTION_KEY not set")
        self.token = token

    def fetch_data(self, database_id) -> requests.Response:
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        response = requests.post(url, headers={"Authorization": f"Bearer {self.token}", "Notion-Version": "2022-06-28"})
        return response


class OKR(Notion):
    database_id: str
    data: pd.DataFrame

    def __init__(self, token: str = "", database_id: str = "") -> None:
        super().__init__(token)
        self.database_id = database_id

    def get_okr(self) -> None:
        result_dict = self.fetch_data(self.database_id).json()

        data = pd.DataFrame(
            columns=["title", "current_value", "target_value", "objective", "assignee", "period", "scope"]
        )

        for item in result_dict["results"]:
            if item["properties"]["Scope"]["select"]:
                if len(item["properties"]["Key Result"]["title"]):
                    title = item["properties"]["Key Result"]["title"][0]["text"]["content"]
                    current_value = item["properties"]["Current Value"]["number"]
                    target_value = item["properties"]["Target Value"]["number"]
                    objective = item["properties"]["Objective"]["select"]["name"]
                    assignee = sorted([person["name"] for person in item["properties"]["Assignee"]["people"]])
                    period = sorted([p["name"] for p in item["properties"]["Period"]["multi_select"]])
                    scope = item["properties"]["Scope"]["select"]["name"]

                    data.loc[-1] = [title, current_value, target_value, objective, assignee, period, scope]
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

    def get_figure_initiatives(self, search_period=None, fnTableHeight=None) -> go:
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
                    header=dict(values=list(initiatives.columns), fill_color="paleturquoise", align="left"),
                    cells=dict(
                        values=[initiatives.title, initiatives.assignee],
                        fill_color="lavender",
                        align="left",
                    ),
                )
            ]
        )
        fig.update_layout(title=fig_title)
        if fnTableHeight:
            fig.update_layout(height=fnTableHeight(initiatives))

        return fig
