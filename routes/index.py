from dash import html, dcc
import plotly.express as px
import pandas as pd

# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more options
df = pd.DataFrame(
    {
        "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
        "Amount": [4, 1, 2, 2, 4, 5],
        "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"],
    }
)

fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")


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
        ]
    )
