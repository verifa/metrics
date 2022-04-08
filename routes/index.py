from dash import html, dcc
import plotly.express as px
from datetime import date
import pandas as pd
import os
from tempoapiclient import client

tempokey=os.environ.get("TEMPO_KEY")

tempo = client.Tempo(
    auth_token=tempokey,
    base_url="https://api.tempo.io/core/3")

worklogs = tempo.get_worklogs(
    dateFrom="2022-01-01",
    dateTo=str(date.today())
    )

rawdata = pd.json_normalize(worklogs)

workdata = rawdata[["issue.key", "timeSpentSeconds", "billableSeconds", "startDate", "author.displayName"]]

fig = px.bar(workdata, 
            x="author.displayName", 
            y="timeSpentSeconds", 
            color="issue.key", 
            barmode="group", height=600)

fig2 = px.bar(workdata, x="issue.key", y="timeSpentSeconds", color="author.displayName")

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
