"""System module."""
import logging
import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go
from dash import dcc, html

from routes.date_utils import lookBack
from routes.notion import OKR
from routes.tempo import SupplementaryData, TempoData

# =========================================================
# Constants
# =========================================================


START_DATE = pd.Timestamp("2021-01-01")
TODAY = pd.Timestamp("today")
YESTERDAY = TODAY - pd.to_timedelta("1day")
ROLLING_DATE = lookBack(180)
TEMPO_CONFIG_PATH = os.environ.get("TEMPO_CONFIG_PATH", "/tempo")

TEMPO_LOG_LEVEL = os.environ.get("TEMPO_LOG_LEVEL", "WARNING")
if TEMPO_LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logging.basicConfig(level=logging.getLevelName(TEMPO_LOG_LEVEL))
else:
    logging.warning(f"{TEMPO_LOG_LEVEL} is not a valid log level, using default: WARNING")

NOTION_KEY = os.environ.get("NOTION_KEY", "")
NOTION_OKR_DATABASE_ID = os.environ.get("NOTION_OKR_DATABASE_ID", "")
NOTION_OKR_LABELS = [["2022", "Q4"], ["2022"]]

COLOR_HEAD = "#ad9ce3"
COLOR_ONE = "#ccecef"
COLOR_TWO = "#fc9cac"

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


def normaliseUserRolling7(frame, working_hours):
    if working_hours.empty:
        result = frame
        result["Daily"] = 8
    else:
        result = frame.merge(working_hours[["User", "Daily"]], on=["User"])
    result["%-billable"] = 100 * (result["Billable"] / (5 * result["Daily"]))
    result["%-internal"] = 100 * (result["Internal"] / (5 * result["Daily"]))

    return result


def normaliseTeamAverage(frame, last):
    df_norm = teamRollingAverage7(frame[frame["Date"] <= last], ["%-billable", "%-internal"])
    df_norm_30 = rollingAverage(df_norm, ["%-billable", "%-internal"], 30)
    df_norm_30.columns = ["Date", "%-billable30", "%-internal30"]
    df_norm = df_norm.merge(df_norm_30, on=["Date"])

    return df_norm


def tableHeight(table, base_height=208):
    total_height = base_height
    for x in range(table.shape[0]):
        total_height += 20
        for y in range(table.shape[1]):
            if len(str(table.iloc[x][y])) > 30:
                total_height += 12
    return total_height


# =========================================================
# Fetch data
# =========================================================


data = TempoData()
data.load(from_date=START_DATE, to_date=YESTERDAY)

supplementary_data = SupplementaryData(TEMPO_CONFIG_PATH)
supplementary_data.load(data.getUsers())

data.zeroOutBillableTime(supplementary_data.internal_keys)

if not supplementary_data.rates.empty:
    data.injectRates(supplementary_data.rates)
    table_rates = data.ratesTable(tableHeight, COLOR_HEAD, COLOR_ONE)
    table_missing_rates = data.missingRatesTable(tableHeight, COLOR_HEAD, COLOR_ONE)

if not supplementary_data.working_hours.empty:
    data.padTheData(supplementary_data.working_hours)


# =========================================================
# Table: User working hours
# =========================================================


table_working_hours = data.tableByUser(supplementary_data.working_hours, tableHeight, COLOR_HEAD, COLOR_ONE)
last_reported = pd.to_datetime(min(data.byUser(supplementary_data.working_hours)["Last"]))
logging.info(f"Last common day: {last_reported}")


# =========================================================
# Figure: Normalised time (individual)
# =========================================================


def figureNormalisedIndividual(data, supplementary_data):
    df_user_time_rolling = data.userRolling7(["Billable", "Internal"])
    df_user_normalised = normaliseUserRolling7(df_user_time_rolling, supplementary_data.working_hours)
    figure_normalised_individual = px.scatter(
        df_user_normalised[df_user_normalised["Date"] > ROLLING_DATE],
        x="Date",
        y=["%-billable", "%-internal"],
        facet_col="User",
        facet_col_wrap=2,
        color_discrete_sequence=["#8FBC8F", "#FF7F50"],
        height=1200,
    )
    figure_normalised_individual.update_layout(title="Normalised data, rolling 7 days", yaxis_title="Work time [%]")
    return figure_normalised_individual


# =========================================================
# Figure: Normalised time (team)
# =========================================================


def figureNormalisedTeam(data, supplementary_data):
    df_user_time_rolling = data.userRolling7(["Billable", "Internal"])
    df_user_normalised = normaliseUserRolling7(df_user_time_rolling, supplementary_data.working_hours)
    df_team_normalised = normaliseTeamAverage(df_user_normalised, last_reported)
    figure_normalised_team = px.scatter(
        df_team_normalised,
        x="Date",
        y=["%-billable", "%-internal", "%-billable30", "%-internal30"],
        color_discrete_sequence=["#8FBC8F", "#FF7F50", "#006400", "#A52A2A"],
        height=800,
    )
    figure_normalised_team.update_layout(title="Normalised team data", yaxis_title="Work time [%]")
    figure_normalised_team.update_layout(
        xaxis_rangeslider_visible=True,
        xaxis_range=[ROLLING_DATE, str(date.today())],
    )
    return figure_normalised_team


# =========================================================
# Figure: Rolling income (individual)
# =========================================================


def figureRollingIncomeIndividual(data):
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
    return figure_rolling_income_individual


# =========================================================
# Figure: Rolling income (team)
# =========================================================


def figureRollingIncomeTeam(data):
    df_user_time_rolling = data.userRolling7("Income")
    df_team_time_rolling_7 = teamRollingAverage7(
        df_user_time_rolling[df_user_time_rolling["Date"] <= last_reported], "Income"
    )
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
        title="Rolling income (average/person)",
        yaxis_title="Income (euro)",
    )
    return figure_rolling_income_team


# =========================================================
# Figure: Rolling total
# =========================================================


def figureRollingTotal(data):
    df_user_time_rolling = data.teamRolling7("Income")
    df_team_time_rolling_30 = rollingAverage(df_user_time_rolling, "Income", 30)
    df_team_time_rolling_30.columns = ["Date", "Income30"]
    df_team_time_rolling_30 = df_team_time_rolling_30.merge(df_user_time_rolling, on=["Date"])
    df_team_rolling_total = df_team_time_rolling_30

    df_raw_costs = supplementary_data.raw_costs

    figure_rolling_total = px.scatter(
        df_team_rolling_total,
        x="Date",
        y=["Income", "Income30"],
        color_discrete_sequence=["#B6B6B6", "#81C784"],
        height=600,
    )
    if not df_raw_costs.empty:
        figure_rolling_total.add_trace(
            go.Scatter(
                x=df_raw_costs["Month"],
                y=df_raw_costs["Weekly"],
                mode="lines",
                line=go.scatter.Line(color="salmon"),
                fill="tozeroy",
                fillcolor="rgba(250,128,114,0.1)",
                name="Costs",
            )
        )
    figure_rolling_total.update_layout(
        title="Rolling income (total)",
        yaxis_title="Income (euro)",
    )
    return figure_rolling_total


# =========================================================
# Figure: Financial plots
# =========================================================


def figureFinancialTotal(data):
    figure_rolling_total = px.scatter(height=600)
    monthly_result = supplementary_data.raw_costs[supplementary_data.raw_costs["In"] != 0]

    figure_rolling_total.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=monthly_result["In"],
            mode="lines",
            line=go.scatter.Line(color="#0F5567"),
            fill="tozeroy",
            fillcolor="rgba(15,85,103,0.1)",
            name="Income",
        )
    )
    figure_rolling_total.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=-monthly_result["Cost"],
            mode="lines",
            line=go.scatter.Line(color="#F0AA98"),
            fill="tozeroy",
            fillcolor="rgba(240,170,152,0.1)",
            name="Costs",
        )
    )
    figure_rolling_total.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=monthly_result["In"] - monthly_result["Cost"],
            mode="lines",
            line=go.scatter.Line(color="#C4C4C4"),
            fill="tozeroy",
            fillcolor="rgba(196,196,196,0.5)",
            name="Result",
        )
    )

    monthly_result = monthly_result[monthly_result["Month"].dt.day == 1]
    monthly_result["Month"] = monthly_result["Month"] + pd.Timedelta("14 days")
    monthly_sum_cost = monthly_result.rolling(12, min_periods=1)["Cost"].sum()
    monthly_sum_in = monthly_result.rolling(12, min_periods=1)["In"].sum()
    monthly_result["Result"] = monthly_sum_in - monthly_sum_cost
    logging.info(monthly_result)

    figure_rolling_total.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=monthly_result["Result"],
            mode="lines+markers",
            line=go.scatter.Line(color="black"),
            name="Cumulative sum 1 year",
        )
    )
    figure_rolling_total.update_layout(
        title="Financials (real data)",
        yaxis_title="€ (euro)",
    )
    return figure_rolling_total


# =========================================================
# Figure: Rolling Income vs. Cost
# =========================================================


def figureRollingEarnings(data):
    df_team_earn_rolling = data.teamRolling7Relative(supplementary_data.costs)
    df_team_earn_rolling_30 = rollingAverage(df_team_earn_rolling, "Diff", 30)
    df_team_earn_rolling_30.columns = ["Date", "Diff30"]
    df_team_earn_rolling_30 = df_team_earn_rolling_30.merge(df_team_earn_rolling, on=["Date"])
    df_team_earn_rolling_365 = rollingAverage(df_team_earn_rolling, "Diff", 365)
    df_team_earn_rolling_365.columns = ["Date", "Diff365"]
    df_team_earn_rolling_365 = df_team_earn_rolling_365.merge(df_team_earn_rolling_30, on=["Date"])
    df_team_rolling_total = df_team_earn_rolling_365

    df_team_rolling_total.rename(
        columns={
            "Diff": "Rolling Weekly Average",
            "Diff30": "Rolling Monthly Average",
            "Diff365": "Rolling Yearly Average",
        },
        inplace=True,
    )

    figure_rolling_earnings = px.scatter(
        df_team_rolling_total,
        x="Date",
        y=["Rolling Weekly Average", "Rolling Monthly Average", "Rolling Yearly Average"],
        color_discrete_sequence=["#C8E6C9", "#77AEE0", "#1B5E20"],
        height=600,
    )
    figure_rolling_earnings.add_hline(y=1, fillcolor="indigo")
    figure_rolling_earnings.add_vrect(
        x0=max(df_team_rolling_total["Date"]) - pd.Timedelta(365, "D"),
        x1=max(df_team_rolling_total["Date"]),
        annotation_text="One Year",
        annotation_position="top left",
        fillcolor="green",
        opacity=0.05,
        line_width=0,
    )
    figure_rolling_earnings.add_vrect(
        x0=max(df_team_rolling_total["Date"]) - pd.Timedelta(30, "D"),
        x1=max(df_team_rolling_total["Date"]),
        annotation_text="30 days",
        annotation_position="top right",
        fillcolor="darkgreen",
        opacity=0.05,
        line_width=0,
    )
    figure_rolling_earnings.update_layout(
        title="Income normalized with cost",
        yaxis_title="Income / Cost",
    )
    return figure_rolling_earnings


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


figure_popular_projects_this_year = px.histogram(
    data.thisYear().sort_values("Key"),
    x="Group",
    y="Time",
    color="User",
    height=600,
    title=f"Popular projects for {data.this_year}",
)
figure_popular_projects_this_year.update_xaxes(categoryorder="total ascending")
figure_popular_projects_this_year.update_layout(yaxis_title="Popular project entries [h]")

figure_popular_projects_last_year = px.histogram(
    data.lastYear().sort_values("Key"),
    x="Group",
    y="Time",
    color="User",
    height=600,
    title=f"Popular projects for {data.last_year}",
)
figure_popular_projects_last_year.update_xaxes(categoryorder="total ascending")
figure_popular_projects_last_year.update_layout(yaxis_title="Popular project entries [h]")


# =========================================================
# Figure: Egg baskets
# -------------------
# Two variants
# - Sum of Income (Euro) if rates data exists
# - Sum of billable time otherwise
# =========================================================


eggs_days_ago = 90
if supplementary_data.rates.empty:
    yAxisTitle = "Sum of billable time"
    figure_eggbaskets = px.histogram(data.byTotalGroup(eggs_days_ago), x="Group", y="Billable", color="User")
    figure_eggbaskets.update_xaxes(categoryorder="total ascending")
    figure_eggbaskets.update_layout(
        title="Sum of billable time (" + str(eggs_days_ago) + " days back)",
    )
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
        title="Baskets for our eggs (" + str(eggs_days_ago) + " days back)",
    )
figure_eggbaskets.update_layout(
    height=600,
    yaxis_title=yAxisTitle,
    bargap=0.1,
)


# =========================================================
# Base rendering (only requires TEMPO_KEY)
# =========================================================


tab_children = [
    dcc.Tab(label="Main", value="start_page"),
    dcc.Tab(label="Billable", value="billable"),
    dcc.Tab(label="Internal", value="internal"),
    dcc.Tab(label="Popular projects", value="popular_projects"),
    dcc.Tab(label="Projects", value="projects"),
]

main_list = [table_working_hours]
if not supplementary_data.rates.empty:
    main_list.append(table_missing_rates)
main_list.append(figure_eggbaskets)

figure_tabs = {
    "start_page": ("Main", main_list),
    "billable": ("Billable work", [figure_billable_this_year, figure_billable_last_year]),
    "internal": ("Internal work", [figure_internal_this_year, figure_internal_last_year]),
    "popular_projects": ("Popular projects", [figure_popular_projects_this_year, figure_popular_projects_last_year]),
    "projects": ("What we work on", [figure_projects_team, figure_projects_individual]),
}


# =========================================================
# Dynamic addition of content
# =========================================================


# ---------------------------------------------------------
# Financial data
# Requires income and costs in config files
if "In" in supplementary_data.costs:
    figure = figureFinancialTotal(data)

    # Add tabs
    figure_tabs["finance"] = ("Finance", [figure])
    tab_children.append(dcc.Tab(label="Finance", value="finance"))

# ---------------------------------------------------------
# Project rates
# Requires config files: rates, workinghours and costs
if not supplementary_data.rates.empty:
    figure_rolling_total = figureRollingTotal(data)
    figure_rolling_income_team = figureRollingIncomeTeam(data)
    figure_rolling_income_individual = figureRollingIncomeIndividual(data)

    # Add tabs
    figure_tabs["rates"] = ("Rates", [table_rates])
    tab_children.append(dcc.Tab(label="Rates", value="rates"))
    figure_tabs["rolling_income"] = (
        "Rolling income",
        [figure_rolling_total, figure_rolling_income_team, figure_rolling_income_individual],
    )
    tab_children.append(dcc.Tab(label="Rolling income", value="rolling_income"))

    if not supplementary_data.costs.empty:
        figure_rolling_earnings = figureRollingEarnings(data)
        # Update main page
        (head, plots) = figure_tabs["start_page"]
        plots.append(figure_rolling_earnings)
        figure_tabs["start_page"] = (head, plots)


# ---------------------------------------------------------
# Normalised working time
# Requires config files: workinghours
if not supplementary_data.working_hours.empty:
    figure_normalised_team = figureNormalisedTeam(data, supplementary_data)
    figure_normalised_individual = figureNormalisedIndividual(data, supplementary_data)

    # Add tab
    figure_tabs["normalised_worktime"] = (
        "Normalised Work Time",
        [figure_normalised_team, figure_normalised_individual],
    )
    tab_children.append(dcc.Tab(label="Normalised Work Time", value="normalised_worktime"))


# ---------------------------------------------------------
# OKR data from NOTION
if NOTION_KEY and NOTION_OKR_DATABASE_ID:
    okr = OKR(NOTION_KEY, NOTION_OKR_DATABASE_ID)
    okr.get_okr()

    okr_figs_kr = [okr.get_figure_key_result(label) for label in NOTION_OKR_LABELS]
    okr_figs_ini = [
        okr.get_figure_initiatives(label, tableHeight, COLOR_HEAD, COLOR_ONE) for label in NOTION_OKR_LABELS
    ]

    # Add tab
    figure_tabs["okr_fig"] = ("OKR", okr_figs_kr + okr_figs_ini)
    tab_children.append(dcc.Tab(label="OKR", value="okr_fig"))

    # Update main page with first NOTION_OKR_LABELS
    (head, plots) = figure_tabs["start_page"]
    plots.append(okr_figs_kr[0])
    plots.append(okr_figs_ini[0])
    figure_tabs["start_page"] = (head, plots)


# =========================================================
# Rendering
# =========================================================


tab_structure = dcc.Tabs(id="tabs-graph", value="start_page", children=tab_children)

pageheader = html.Div(
    [
        dcc.Markdown("## Verifa Metrics Dashboard"),
        dcc.Markdown(f"""#### {START_DATE.strftime("%b %d, %Y")} ➜ {YESTERDAY.strftime("%b %d, %Y")}"""),
    ]
)


def render_content(tab):
    (head, plots) = figure_tabs[tab]
    sections = [dcc.Graph(id="plot", figure=figure) for figure in plots]
    sections.insert(0, dcc.Markdown("### " + head))
    return html.Div(html.Section(children=sections))
