from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd

external_scripts = [
    # Import TailwindCSS
    "https://tailwindcss.com/",
    {"src": "https://cdn.tailwindcss.com"},
]
external_stylesheets = external_stylesheets = [
    # Import Outfit Google Font
    "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap",
]

app = Dash(
    __name__,
    external_scripts=external_scripts,
    external_stylesheets=external_stylesheets,
)

app.css.config.serve_locally = True
app.scripts.config.serve_locally = True

# Setup the server for gunicorn (prod)
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
    app.run_server(debug=True, host="127.0.0.1")
