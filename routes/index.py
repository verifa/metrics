"""System module."""
import os
from datetime import date

import pandas as pd
import plotly.express as px
from dash import dcc, html
from tempoapiclient import client

# really wanted this in tempo/tempodata.py but
# could not convince poetry to accept it
tempokey = os.environ.get("TEMPO_KEY")

tempo = client.Tempo(
    auth_token=tempokey,
    base_url="https://api.tempo.io/core/3")


class TempoData:
    """Tempo data class."""

    def __init__(self, fromDate, toDate):
        self.from_date = fromDate
        self.to_date = toDate
        self.logs = tempo.get_worklogs(
            dateFrom="2022-01-01",
            dateTo=str(date.today())
        )
        self.raw = pd.json_normalize(self.logs)
        self.data = self.raw[[
            "issue.key",
            "timeSpentSeconds",
            "billableSeconds",
            "startDate",
            "author.displayName"]]
        self.data.columns = [
            "Key",
            "Time",
            "Billable",
            "Date",
            "User"]


work = TempoData("2022-01-01", str(date.today()))

fig = px.bar(
    work.data,
    x="User",
    y="Time",
    color="Key",
    barmode="group", height=600)

fig2 = px.bar(
    work.data,
    x="Key",
    y="Time",
    color="User",
    height=600)


def render() -> html._component:
    """Renders the HTML components for this page"""
    return html.Div(
        children=[
            html.Section(html.H1(children="Verifa Metrics Dashboard")),
            html.Section(render_summary()),
            html.Section(render_chart()),
        ]
    )


def render_summary() -> html._component:
    """Render summary"""
    return html.Div(
        className="",
        children=[
            html.H3("Last 30 Days"),
            html.Div(
                children=[
                    html.Dl(
                        className="grid  grid-cols-1 gap-5 sm:grid-cols-3",
                        children=[
                            html.Div(
                                className="px-4 py-5 bg-white",
                                children=[
                                    html.Dt(
                                        className="text-v-pink truncate",
                                        children="Some value",
                                    ),
                                    html.Dd(
                                        className="text-3xl text-v-black",
                                        children="123",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="px-4 py-5 bg-white",
                                children=[
                                    html.Dt(
                                        className="text-v-pink truncate",
                                        children="Some value",
                                    ),
                                    html.Dd(
                                        className="text-3xl text-v-black",
                                        children="123",
                                    ),
                                ],
                            ),
                            html.Div(
                                className="px-4 py-5 bg-white",
                                children=[
                                    html.Dt(
                                        className="text-v-pink truncate",
                                        children="Some value",
                                    ),
                                    html.Dd(
                                        className="text-3xl text-v-black",
                                        children="123",
                                    ),
                                ],
                            ),
                        ],
                    )
                ]
            ),
        ],
    )


def render_chart() -> html._component:
    """Render chart"""
    return html.Div(
        children=[
            html.P(
                children="""
        Dash: A web application framework for your data.
    """
            ),
            dcc.Graph(id="example-graph", figure=fig),
            dcc.Graph(id="example-2", figure=fig2)
        ]
    )
