"""System module."""
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import dcc, html

from routes.date_utils import lookBack
from routes.tempo import SupplementaryData, TempoData

# =========================================================
# Constants
# =========================================================


START_DATE = pd.Timestamp("2021-01-01")
TODAY = pd.Timestamp("today")
ROLLING_DATE = lookBack(180)


# =========================================================
# Helpers
# =========================================================


def teamRollingAverage7(frame, to_mean):
    return frame.groupby(["Date"])[to_mean].mean().reset_index(inplace=False)


def rollingAverage(frame, to_mean, days, offset=7):
    return (
        frame.set_index("Date")
        .rolling(str(days) + "d", min_periods=days - offset)[to_mean]
        .mean()
        .reset_index(inplace=False)
    )


# =========================================================
# Fetch data
# =========================================================


data = TempoData()
data.load(from_date=START_DATE, to_date=TODAY)

supplementary_data = SupplementaryData()
supplementary_data.load(data.getUsers())

data.injectRates(supplementary_data.rates)


# =========================================================
# Table: User working hours
# =========================================================


table_working_hours = ff.create_table(data.byUser(supplementary_data.working_hours))


# =========================================================
# Table: Project rates
# =========================================================


table_rates = ff.create_table(data.ratesTable())


# =========================================================
# Figure: Rolling time (individual)
# =========================================================


df_user_time_rolling = data.userRolling7(["Billable", "Internal"])
figure_rolling_time_individual = px.scatter(
    df_user_time_rolling[df_user_time_rolling["Date"] > ROLLING_DATE],
    x="Date",
    y=["Billable", "Internal"],
    facet_col="User",
    facet_col_wrap=3,
    height=800,
)
figure_rolling_time_individual.update_layout(title="Rolling 7 days")


# =========================================================
# Figure: Rolling time (team)
# =========================================================


df_team_time_rolling_7 = teamRollingAverage7(df_user_time_rolling, ["Billable", "Internal"])
df_team_time_rolling_30 = rollingAverage(df_team_time_rolling_7, ["Billable", "Internal"], 30)
df_team_time_rolling_30.columns = ["Date", "Billable30", "Internal30"]
df_team_time_rolling_30 = df_team_time_rolling_30.merge(df_team_time_rolling_7, on=["Date"])
figure_rolling_time_team = px.scatter(
    df_team_time_rolling_30,
    x="Date",
    y=["Billable", "Billable30", "Internal", "Internal30"],
    color_discrete_sequence=["#8FBC8F", "#006400", "#FF7F50", "#A52A2A"],
    height=600,
)
figure_rolling_time_team.update_layout(
    xaxis_rangeslider_visible=True,
    xaxis_range=[ROLLING_DATE, str(date.today())],
)


# =========================================================
# Figure: Rolling income (individual)
# =========================================================


df_user_time_rolling = data.userRolling7("Income")
figure_rolling_income_individual = px.scatter(
    df_user_time_rolling[df_user_time_rolling["Date"] > ROLLING_DATE],
    x="Date",
    y="Income",
    facet_col="User",
    facet_col_wrap=3,
    height=800,
)
figure_rolling_income_individual.update_layout(title="Rolling 7 days (income)")


# =========================================================
# Figure: Rolling income (team)
# =========================================================


df_team_time_rolling_7 = teamRollingAverage7(df_user_time_rolling, "Income")
df_team_time_rolling_30 = rollingAverage(df_team_time_rolling_7, "Income", 30)
df_team_time_rolling_30.columns = ["Date", "Income30"]
df_team_time_rolling_30 = df_team_time_rolling_30.merge(df_team_time_rolling_7, on=["Date"])
figure_rolling_income_team = px.scatter(
    df_team_time_rolling_30,
    x="Date",
    y=["Income", "Income30"],
    color_discrete_sequence=["#8FBC8F", "#006400"],
    height=600,
)
figure_rolling_income_team.update_layout(
    yaxis_title="Income (euro)",
    xaxis_rangeslider_visible=True,
    xaxis_range=[ROLLING_DATE, str(date.today())],
)


# =========================================================
# Figure: Rolling total
# =========================================================


df_user_time_rolling = data.teamRolling7("Income")
df_team_time_rolling_30 = rollingAverage(df_user_time_rolling, "Income", 30)
df_team_time_rolling_30.columns = ["Date", "Income30"]
df_team_time_rolling_30 = df_team_time_rolling_30.merge(df_user_time_rolling, on=["Date"])
df_team_rolling_total_90 = rollingAverage(df_user_time_rolling, "Income", 90)
df_team_rolling_total_90.columns = ["Date", "Income90"]
df_team_rolling_total_90 = df_team_rolling_total_90.merge(df_team_time_rolling_30, on=["Date"])
df_team_rolling_total_365 = rollingAverage(df_user_time_rolling, "Income", 365)
df_team_rolling_total_365.columns = ["Date", "Income365"]
df_team_rolling_total_365 = df_team_rolling_total_365.merge(df_team_rolling_total_90, on=["Date"])
df_team_rolling_total = df_team_rolling_total_365

figure_rolling_total = px.scatter(
    df_team_rolling_total,
    x="Date",
    y=["Income", "Income30", "Income90", "Income365"],
    color_discrete_sequence=["#C8E6C9", "#81C784", "#388E3C", "#1B5E20"],
    height=600,
)
figure_rolling_total.update_layout(
    yaxis_title="Income (euro)",
    xaxis_rangeslider_visible=True,
    xaxis_range=[ROLLING_DATE, str(date.today())],
)


# =========================================================
# Figure: Projects (individual)
# =========================================================


df_by_group = data.byGroup().sort_values("Group")
figure_projects_individual = px.histogram(
    df_by_group[df_by_group["Date"] > ROLLING_DATE],
    x="Date",
    y="Time",
    color="Group",
    facet_col="User",
    facet_col_wrap=3,
    height=800,
)
figure_projects_individual.update_layout(bargap=0.1)


# =========================================================
# Figure: Projects (team)
# =========================================================


df_by_group = data.byGroup().sort_values("Group")
figure_projects_team = px.histogram(
    df_by_group[df_by_group["Date"] > ROLLING_DATE], x="Date", y="Time", color="Group", height=600
)
figure_projects_team.update_layout(bargap=0.1)


# =========================================================
# Figure: Billable time
# =========================================================

# a figure for this year
figure_billable_this_year = px.histogram(
    data.thisYear().sort_values("Key"),
    x="User",
    y="Billable",
    color="Key",
    height=600,
    title=f"Billable entries for {data.this_year}",
)

figure_billable_this_year.update_xaxes(categoryorder="total ascending")
figure_billable_this_year.update_layout(yaxis_title="Billable entries [h]")

# a figure for last year
figure_billable_last_year = px.histogram(
    data.lastYear().sort_values("Key"),
    x="User",
    y="Billable",
    color="Key",
    height=600,
    title=f"Billable entries for {data.last_year}",
)

figure_billable_last_year.update_xaxes(categoryorder="total ascending")
figure_billable_last_year.update_layout(yaxis_title="Billable entries [h]")


# =========================================================
# Figure: Internal time
# =========================================================


figure_internal_this_year = px.histogram(
    data.thisYear().sort_values("Key"),
    x="User",
    y="Internal",
    color="Key",
    height=600,
    title=f"Internal entries for {data.this_year}",
)

figure_internal_this_year.update_xaxes(categoryorder="total descending")
figure_internal_this_year.update_layout(yaxis_title="Internal entries [h]")

figure_internal_last_year = px.histogram(
    data.lastYear().sort_values("Key"),
    x="User",
    y="Internal",
    color="Key",
    height=600,
    title=f"Internal entries for {data.last_year}",
)

figure_internal_last_year.update_xaxes(categoryorder="total descending")
figure_internal_last_year.update_layout(yaxis_title="Internal entries [h]")


# =========================================================
# Figure: Popular projects
# =========================================================


figure_popular_projects = px.histogram(data.data, x="Group", y="Time", color="User", height=600)

figure_popular_projects.update_xaxes(categoryorder="total ascending")


# =========================================================
# Figure: Egg baskets
# =========================================================


eggs_days_ago = 90
if supplementary_data.rates.empty:
    yAxisTitle = "Sum of billable time"
    figure_eggbaskets = px.histogram(data.byTotalGroup(eggs_days_ago), x="Group", y="Billable", color="User")
    figure_eggbaskets.update_xaxes(categoryorder="total ascending")
else:
    yAxisTitle = "Sum of Income (Euro)"
    figure_eggbaskets = px.histogram(
        data.byEggBaskets(),
        x="Group",
        y="Income",
        color="User",
        facet_col="TimeBasket",
        facet_col_wrap=3,
        category_orders={"TimeBasket": ["60-90 days ago", "30-60 days ago", "0-30 days ago"]},
    )

figure_eggbaskets.update_layout(
    height=600, yaxis_title=yAxisTitle, bargap=0.1, title="Baskets for our eggs (" + str(eggs_days_ago) + " days back)"
)


# =========================================================
# Rendering
# =========================================================


tabStructure = dcc.Tabs(
    id="tabs-graph",
    value="start_page",
    children=[
        dcc.Tab(label="Main", value="start_page"),
        dcc.Tab(label="Rates", value="rates"),
        dcc.Tab(label="Billable", value="billable"),
        dcc.Tab(label="Internal", value="internal"),
        dcc.Tab(label="Popular projects", value="popular_projects"),
        dcc.Tab(label="Projects", value="projects"),
        dcc.Tab(label="Rolling time", value="rolling_time"),
        dcc.Tab(label="Rolling income", value="rolling_income"),
    ],
)

pageheader = html.Div(
    [
        dcc.Markdown("## Verifa Metrics Dashboard"),
        dcc.Markdown(f"""#### {START_DATE.strftime("%b %d, %Y")} ➜ {TODAY.strftime("%b %d, %Y")}"""),
    ]
)


figure_tabs = {
    "start_page": ("Main", [table_working_hours, figure_rolling_total, figure_eggbaskets]),
    "rates": ("Rates", [table_rates]),
    "billable": ("Billable work", [figure_billable_this_year, figure_billable_last_year]),
    "internal": ("Internal work", [figure_internal_this_year, figure_internal_last_year]),
    "popular_projects": ("Popular projects", [figure_popular_projects]),
    "projects": ("What we work on", [figure_projects_team, figure_projects_individual]),
    "rolling_time": (
        "Team average, rolling 7 days, based on time",
        [figure_rolling_time_team, figure_rolling_time_individual],
    ),
    "rolling_income": (
        "Team average, rolling 7 days, based on income",
        [figure_rolling_income_team, figure_rolling_income_individual],
    ),
}


def render_content(tab):
    (head, plots) = figure_tabs[tab]
    sections = [dcc.Graph(id="plot", figure=figure) for figure in plots]
    sections.insert(0, dcc.Markdown("### " + head))
    # sections = dcc.Markdown("## " + head)
    return html.Div(html.Section(children=sections))
