"""
The metrics dash app with data from tempo
"""

import os

from dash import Dash, html
from dash.dependencies import Input, Output

from metrics import index

TEMPO_DEVELOPMENT = os.getenv("TEMPO_DEVELOPMENT", "False")

print(f"TEMPO_DEVELOPMENT: {TEMPO_DEVELOPMENT}")

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

app.layout = html.Div(
    className="px-8", children=[index.pageheader, index.tab_structure, html.Div(id="tabs-content-graph")]
)


@app.callback(Output("tabs-content-graph", "children"), Input("tabs-graph", "value"))
def render_content(tab):
    return index.render_content(tab)


if __name__ == "__main__":
    if TEMPO_DEVELOPMENT == "True":
        app.run_server(debug=True, host="127.0.0.1")
    else:
        app.run_server(debug=False, host="127.0.0.1")
