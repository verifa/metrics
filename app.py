from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd

from routes import index

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

app.layout = html.Div(children = [
    index.pageheader,
    index.tabStructure,
    html.Div(id='tabs-content-graph')
])


@app.callback(
    Output('tabs-content-graph', 'children'),
    Input('tabs-graph', 'value'))
def render_content(tab):
    return index.render_content(tab)

if __name__ == "__main__":
    app.run_server(debug=True, host="127.0.0.1")
