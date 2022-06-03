"""System module."""
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import dcc, html

from routes.date_utils import lookAhead, lookBack
from routes.tempo import SupplementaryData, TempoData

# =========================================================
# Constants
# =========================================================


START_DATE = pd.Timestamp("2021-01-01")
TODAY = pd.Timestamp("today")
FIRST_WEEK = lookAhead(7, START_DATE)
FIRST_MONTH = lookAhead(30, START_DATE)
FIRST_QUARTER = lookAhead(90, START_DATE)
FIRST_YEAR = lookAhead(365, START_DATE)
ROLLING_DATE = lookBack(180)


# =========================================================
# Helpers
# =========================================================


def teamRollingAverage7(frame, to_mean):
    return frame.groupby(["Date"])[to_mean].mean().reset_index(inplace=False)


def rollingAverage(frame, to_mean, days):
    return frame.set_index("Date").rolling(str(days) + "d")[to_mean].mean().reset_index(inplace=False)


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
df_user_time_rolling.loc[df_user_time_rolling["Date"] < FIRST_WEEK, "Billable"] = np.nan
df_user_time_rolling.loc[df_user_time_rolling["Date"] < FIRST_WEEK, "Internal"] = np.nan
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
df_team_time_rolling_30.loc[df_team_time_rolling_30["Date"] < FIRST_MONTH, "Billable30"] = np.nan
df_team_time_rolling_30.loc[df_team_time_rolling_30["Date"] < FIRST_MONTH, "Internal30"] = np.nan
df_team_time_rolling_30 = df_team_time_rolling_30.merge(df_team_time_rolling_7, on=["Date"])
figure_rolling_time_team = px.scatter(
    df_team_time_rolling_30,
    x="Date",
    y=["Billable", "Billable30", "Internal", "Internal30"],
    color_discrete_sequence=["#8FBC8F", "#006400", "#FF7F50", "#A52A2A"],
    height=600,
)
figure_rolling_time_team.update_layout(
    title="Team average, rolling 7 days, based on time",
    xaxis_rangeslider_visible=True,
    xaxis_range=[ROLLING_DATE, str(date.today())],
)


# =========================================================
# Figure: Rolling income (individual)
# =========================================================


df_user_time_rolling = data.userRolling7("Income")
df_user_time_rolling.loc[df_user_time_rolling["Date"] < FIRST_WEEK, "Income"] = np.nan
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
df_team_time_rolling_30.loc[df_team_time_rolling_30["Date"] < FIRST_MONTH, "Income30"] = np.nan
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
    title="Team average, rolling 7 days, based on income",
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
df_team_rolling_total.loc[df_team_rolling_total["Date"] < FIRST_WEEK, "Income"] = np.nan
df_team_rolling_total.loc[df_team_rolling_total["Date"] < FIRST_MONTH, "Income30"] = np.nan
df_team_rolling_total.loc[df_team_rolling_total["Date"] < FIRST_QUARTER, "Income90"] = np.nan
df_team_rolling_total.loc[df_team_rolling_total["Date"] < FIRST_YEAR, "Income365"] = np.nan

figure_rolling_total = px.scatter(
    df_team_rolling_total,
    x="Date",
    y=["Income", "Income30", "Income90", "Income365"],
    color_discrete_sequence=["#C8E6C9", "#81C784", "#388E3C", "#1B5E20"],
    height=600,
)
figure_rolling_total.update_layout(
    yaxis_title="Income (euro)",
    title="Weekly income",
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
figure_projects_individual.update_layout(bargap=0.1, title="What do we work on")


# =========================================================
# Figure: Projects (team)
# =========================================================


df_by_group = data.byGroup().sort_values("Group")
figure_projects_team = px.histogram(
    df_by_group[df_by_group["Date"] > ROLLING_DATE], x="Date", y="Time", color="Group", height=600
)
figure_projects_team.update_layout(bargap=0.1, title="What do we work on")


# =========================================================
# Figure: Billable time
# =========================================================


figure_billable = px.histogram(data.data.sort_values("Key"), x="User", y="Billable", color="Key", height=600)

figure_billable.update_xaxes(categoryorder="total ascending")


# =========================================================
# Figure: Internal time
# =========================================================


figure_internal = px.histogram(data.data.sort_values("Key"), x="User", y="Internal", color="Key", height=600)

figure_internal.update_xaxes(categoryorder="total descending")


# =========================================================
# Figure: Popular projects
# =========================================================


figure_popular_projects = px.histogram(data.data, x="Group", y="Time", color="User", height=600)

figure_popular_projects.update_xaxes(categoryorder="total ascending")


# =========================================================
# Figure: Egg baskets
# =========================================================


days_ago = 90
if supplementary_data.rates.empty:
    yAxisTitle = "Sum of billable time"
    figure_eggbaskets = px.histogram(data.byTotalGroup(days_ago), x="Group", y="Billable", color="User")
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
    height=600, yaxis_title=yAxisTitle, bargap=0.1, title="Baskets for our eggs (" + str(days_ago) + " days back)"
)


# =========================================================
# Rendering
# =========================================================


tabStructure = dcc.Tabs(
    id="tabs-graph",
    value="working_hours",
    children=[
        dcc.Tab(label="Our hours", value="working_hours"),
        dcc.Tab(label="Rates", value="rates"),
        dcc.Tab(label="Billable", value="billable"),
        dcc.Tab(label="Internal", value="internal"),
        dcc.Tab(label="Popular projects", value="popular_projects"),
        dcc.Tab(label="Projects", value="projects"),
        dcc.Tab(label="Egg Baskets", value="eggbaskets"),
        dcc.Tab(label="Rolling time", value="rolling_time"),
        dcc.Tab(label="Rolling income", value="rolling_income"),
        dcc.Tab(label="Company weekly income", value="rolling_total"),
    ],
)

pageheader = html.Div(
    [
        dcc.Markdown("## Verifa Metrics Dashboard"),
        dcc.Markdown(f"""#### {START_DATE.strftime("%b %d, %Y")} ➜ {TODAY.strftime("%b %d, %Y")}"""),
    ]
)


figure_tabs = {
    "working_hours": [table_working_hours],
    "rates": [table_rates],
    "billable": [figure_billable],
    "internal": [figure_internal],
    "popular_projects": [figure_popular_projects],
    "projects": [figure_projects_team, figure_projects_individual],
    "eggbaskets": [figure_eggbaskets],
    "rolling_time": [figure_rolling_time_team, figure_rolling_time_individual],
    "rolling_income": [figure_rolling_income_team, figure_rolling_income_individual],
    "rolling_total": [figure_rolling_total],
}


def render_content(tab):
    sections = [dcc.Graph(id="plot", figure=figure) for figure in figure_tabs[tab]]
    return html.Div(html.Section(children=sections))
