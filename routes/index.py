"""System module."""
import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import dcc, html
from tempoapiclient import client

# really wanted this in tempo/tempodata.py but
# could not convince poetry to accept it
tempokey = os.environ.get("TEMPO_KEY")

tempo = client.Tempo(
    auth_token=tempokey,
    base_url="https://api.tempo.io/core/3")


class TempoConfig:
    """TempoConfig data class"""
    # where to find the config files
    configPath = os.environ.get("TEMPO_CONFIG_PATH")
    if configPath is None:
        # default path
        configPath = '/tempo'
    # which config files are possible
    workingHoursFile = configPath + "/workinghours.json"

    def __init__(self):
        self.workingHours = pd.DataFrame()
        if os.path.exists(self.workingHoursFile):
            self.workingHours = pd.read_json(self.workingHoursFile)


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
        self.data.loc[:, ('Internal')] = (
            self.data.loc[:, ('Time')] -
            self.data.loc[:, ('Billable')])

    def byDay(self):
        """returns aggregated time and billable time
        grouped by date, user and issue key
        """
        return(
            self.data.groupby(
                ['Date', 'User', 'Key'], as_index=False)
            [['Time', 'Billable']].sum())

    def byUser(self, workingHours=None):
        """returns aggregated time and billable time
        grouped by user
        """
        userData = (
            self.data.groupby('User', as_index=False)
            [['Time', 'Billable']].sum()
        )
        if not workingHours.empty:
            print(workingHours)
            tmpData = pd.merge(userData, workingHours, on="User")
            userData = tmpData

        return(
            userData
        )

    def userRolling7(self):
        """returns rolling 7 day sums for Billable and non Billable time
        grouped by user
        """
        dailySum = (
            self.data.groupby(
                ['Date', 'User'], as_index=False)
            [['Billable', 'Internal']].sum()
        )
        rolling7Sum = (
            dailySum.set_index('Date').groupby(
                ['User'], as_index=False).rolling('7d')
            [['Billable', 'Internal']].sum()
        )
        return(
            rolling7Sum.reset_index(inplace=False)
        )


# read config files
tc = TempoConfig()
# Fetch the data from tempo
work = TempoData("2022-01-01", str(date.today()))
rolling7 = work.userRolling7()

table1 = ff.create_table(work.byUser(tc.workingHours))

rollingAll = px.scatter(
    rolling7,
    x='Date',
    y=['Billable', 'Internal'],
    facet_col='User',
    facet_col_wrap=3,
    height=800
)

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

internal = px.bar(
    work.data,
    x="User",
    y="Internal",
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
            dcc.Graph(id="Aggregated", figure=table1),
            dcc.Graph(id="Billable", figure=billable),
            dcc.Graph(id="Internal", figure=internal),
            dcc.Graph(id="example-2", figure=fig2),
            html.P(
                children="""
                What do we work on
                """
            ),
            dcc.Graph(id="TimeSeries1", figure=time1),
            dcc.Graph(id="TimeSeries2", figure=time2),
            html.P(
                children="""
                Rolling 7 days
                """
            ),
            dcc.Graph(id="Rolling", figure=rollingAll)
        ]
    )
