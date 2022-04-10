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
        self.data.loc[:, ('Date')] = pd.to_datetime(
            self.data.loc[:, ('Date')], format='%Y-%m-%d')
        self.data.loc[:, ('Time')] = self.data.loc[:, ('Time')]/3600
        self.data.loc[:, ('Billable')] = self.data.loc[:, ('Billable')]/3600
        self.data.loc[:, ('Unbillable')] = (
            self.data.loc[:, ('Time')] -
            self.data.loc[:, ('Billable')])

    def byDay(self):
        """returns aggregated time and billable time
        grouped by date, user and issue key
        """
        return(
            self.data.groupby(
                ['Date', 'User', 'Key'], as_index=False)
            ['Time', 'Billable'].sum())


# Fetch the data from tempo
work = TempoData("2022-01-01", str(date.today()))

time1 = px.bar(
    work.byDay(),
    x='Date',
    y='Time',
    color='Key',
    facet_col='User',
    facet_col_wrap=3,
    height=800
)

time2 = px.bar(
    work.byDay(),
    x='Date',
    y='Time',
    color='Key',
    height=600
)

billable = px.bar(
    work.data,
    x="User",
    y="Billable",
    color="Key",
    barmode="group",
    height=600)

unbillable = px.bar(
    work.data,
    x="User",
    y="Unbillable",
    color="Key",
    barmode="group",
    height=600)

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
            dcc.Graph(id="Billable", figure=billable),
            dcc.Graph(id="Unbillable", figure=unbillable),
            dcc.Graph(id="example-2", figure=fig2),
            html.P(
                children="""
                What do we work on
                """
            ),
            dcc.Graph(id="TimeSeries1", figure=time1),
            dcc.Graph(id="TimeSeries2", figure=time2)
        ]
    )
