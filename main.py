from dash import Dash, html, dcc
import flask
import plotly.express as px
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description="Verifa Metrics Dashboard")
parser.add_argument(
    "--debug",
    action="store_true",
    # required=False,
    default=False,
    help="whether to run in debug mode or not",
)

app = Dash(__name__)
server = app.server

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

app.layout = html.Div(
    children=[
        html.H1(children="Hello Dash"),
        html.Div(
            children="""
        Dash: A web application framework for your data.
    """
        ),
        dcc.Graph(id="example-graph", figure=fig),
    ]
)

if __name__ == "__main__":
    args = parser.parse_args()
    app.run_server(debug=True, host="127.0.0.1")
