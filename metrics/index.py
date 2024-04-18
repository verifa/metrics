"""The metrics module."""

import logging
import os
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from metrics.date_utils import lookBack
from metrics.notion import OKR, Allocations, Crew, Financials, WorkingHours
from metrics.supplementary_data import SupplementaryData
# fmt: off
from metrics.tempo_config import (ALLOCATION_START, EUR2SEK, ROLLING_DATE,
                                  START_DATE, TODAY, YESTERDAY)
# fmt: on
from metrics.tempo_data import TempoData

# happy hack until we can fix these
pd.options.mode.chained_assignment = None  # default='warn'

# =========================================================
# Constants
# =========================================================


TEMPO_CONFIG_PATH = os.environ.get("TEMPO_CONFIG_PATH", "/tempo")
TEMPO_DAILY_HOURS = os.environ.get("TEMPO_DAILY_HOURS", 8)

TEMPO_LOG_LEVEL = os.environ.get("TEMPO_LOG_LEVEL", "WARNING")
if TEMPO_LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logging.basicConfig(level=logging.getLevelName(TEMPO_LOG_LEVEL))
else:
    logging.warning("%s {} is not a valid log level, using default: WARNING", TEMPO_LOG_LEVEL)

NOTION_KEY = os.environ.get("NOTION_KEY", "")
NOTION_OKR_DATABASE_ID = os.environ.get("NOTION_OKR_DATABASE_ID", "")
NOTION_FINANCIAL_DATABASE_ID = os.environ.get("NOTION_FINANCIAL_DATABASE_ID", "")
NOTION_WORKINGHOURS_DATABASE_ID = os.environ.get("NOTION_WORKINGHOURS_DATABASE_ID", "")
NOTION_ALLOCATION_DATABASE_ID = os.environ.get("NOTION_ALLOCATIONS_DATABASE_ID", "")
NOTION_CREW_DATABASE_ID = os.environ.get("NOTION_CREW_DATABASE_ID", "")
NOTION_OKR_LABELS = [["2023VH"], ["2023VC"], ["2023EY"]]

COLOR_HEAD = "#ad9ce3"
COLOR_ONE = "#ccecef"
COLOR_TWO = "#fc9cac"

# Configure tabs to show in the UI
SHOWTAB_BILLABLE = False
SHOWTAB_COMPARISON = True
SHOWTAB_INTERNAL = False
SHOWTAB_POPULAR_PROJECTS = False
SHOWTAB_PAYING_PROJECTS = True
SHOWTAB_PROJECTS = True
SHOWTAB_FINANCE = True
SHOWTAB_RATES = False
SHOWTAB_ROLLING_INCOME = True
SHOWTAB_NORMALISED_WORKTIME = True
SHOWTAB_OKR_FIG = False
SHOWMAIN_OKR_FIG = False

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


def normaliseUserRolling7(frame, working_hours_data):
    first_date = START_DATE
    last_date = TODAY
    result = frame
    result["Daily"] = float(TEMPO_DAILY_HOURS)
    if not working_hours_data.empty:
        for _, row in working_hours_data.iterrows():
            if row["Daily"] != float(TEMPO_DAILY_HOURS):
                logging.debug("%s %s", row["User"], row["Daily"])
                if row["Start"] != "*":
                    first_date = row["Start"]
                if row["Stop"] != "*":
                    last_date = row["Stop"]
                result.loc[
                    (result["User"] == row["User"]) & (result["Date"] >= first_date) & (result["Date"] <= last_date),
                    "Daily",
                ] = row["Daily"]

    result["%-billable"] = 100 * (result["Billable"] / (5 * result["Daily"]))
    result["%-internal"] = 100 * (result["Internal"] / (5 * result["Daily"]))

    return result


def normaliseTeamAverage(frame):
    df_norm = teamRollingAverage7(frame, ["%-billable", "%-internal"])
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

start = datetime.now()
logging.info("Starting %s", start)


def delta(txt):
    diff = datetime.now() - start
    logging.info("%s: %s", diff, txt)


# ---------------------------------------------------------
# Data from NOTION
if NOTION_KEY and NOTION_FINANCIAL_DATABASE_ID:
    financials = Financials(NOTION_KEY, NOTION_FINANCIAL_DATABASE_ID)
    financials.get_financials()
    financials_df = financials.data
else:
    financials_df = pd.DataFrame()

delta("Notion Financials")

if NOTION_KEY and NOTION_WORKINGHOURS_DATABASE_ID:
    working_hours = WorkingHours(NOTION_KEY, NOTION_WORKINGHOURS_DATABASE_ID)
    working_hours.get_workinghours()
    working_hours_df = working_hours.data
else:
    working_hours_df = pd.DataFrame()

delta("Notion working Hours")

if NOTION_KEY and NOTION_ALLOCATION_DATABASE_ID:
    allocations = Allocations(NOTION_KEY, NOTION_ALLOCATION_DATABASE_ID)
    allocations.get_allocations()
    allocations_df = allocations.data
else:
    allocations_df = pd.DataFrame()

delta("Notion Allocations")

if NOTION_KEY and NOTION_CREW_DATABASE_ID:
    crew = Crew(NOTION_KEY, NOTION_CREW_DATABASE_ID)
    crew.get_crew()
    crew_df = crew.data
else:
    crew_df = pd.DataFrame()

delta("Notion Crew")

tempo = TempoData()
tempo.load(from_date=START_DATE, to_date=YESTERDAY)
delta("TempoData")

supplementary = SupplementaryData(TEMPO_CONFIG_PATH, financials_df, working_hours_df)
supplementary.load(tempo.getUsers())
delta("Supplementary Data")

tempo.zeroOutBillableTime(supplementary.internal_keys)
delta("ZeroOutBillable")

if not supplementary.rates.empty:
    tempo.injectRates(supplementary.rates)
    delta("InjectRates")
    table_rates = tempo.ratesTable(tableHeight, COLOR_HEAD, COLOR_ONE)
    delta("Table Rates")
    table_missing_rates = tempo.missingRatesTable(tableHeight, COLOR_HEAD, COLOR_ONE)
    delta("Table Missing Rates")

if not supplementary.working_hours.empty:
    tempo.padTheData(supplementary.working_hours)
    delta("Data Padding")

# a quick test
td = tempo.data[tempo.data["Income"] > 0]
print(td)
print(pd.Timestamp("today").strftime("%Y-%m-01"))
print(lookBack(180).strftime("%Y-%m-01"))
td = td[td["Date"] >= lookBack(180).strftime("%Y-%m-01")]
td["Month"] = td["Date"].dt.month
print(td)
print(td.groupby(["Year", "Month", "Key"], as_index=False)["Income"].sum())
# =========================================================
# Table: User working hours
# =========================================================


table_working_hours = tempo.tableByUser(supplementary.working_hours, tableHeight, COLOR_HEAD, COLOR_ONE)
delta("Table Working Hours")
last_reported = pd.to_datetime(min(tempo.byUser(supplementary.working_hours)["Last"]))
logging.info("Last common day: %s", last_reported)

if not supplementary.working_hours.empty:
    df_user_time_rolling = tempo.userRolling7(["Billable", "Internal"])
    delta("User Time Rolling")
    df_user_normalised = normaliseUserRolling7(df_user_time_rolling, supplementary.working_hours)
    delta("User Normalised")
    df_team_normalised = normaliseTeamAverage(df_user_normalised)
    delta("Team Normalised")
    if not supplementary.rates.empty:
        df_user_income_rolling = tempo.userRolling7("Income")
        delta("User Income Rolling")
        # Average user data
        df_average_income_rolling_7 = teamRollingAverage7(df_user_income_rolling, "Income")
        df_average_income_rolling_30 = rollingAverage(df_average_income_rolling_7, "Income", 30)
        df_average_income_rolling_30.columns = ["Date", "Income30"]
        df_average_income_rolling_30 = df_average_income_rolling_30.merge(df_average_income_rolling_7, on=["Date"])
        delta("Average Income Rolling")
        # Team total data
        df_team_income_rolling = tempo.teamRolling7("Income")
        df_team_income_rolling_30 = rollingAverage(df_team_income_rolling, "Income", 30)
        df_team_income_rolling_30.columns = ["Date", "Income30"]
        df_team_income_rolling_30 = df_team_income_rolling_30.merge(df_team_income_rolling, on=["Date"])
        df_team_rolling_total = df_team_income_rolling_30
        delta("User Income Rolling")
        # data for rolling earnings
        if not supplementary.costs.empty:
            df_team_earn_rolling = tempo.teamRolling7Relative(supplementary.costs)
            df_team_earn_rolling_30 = rollingAverage(df_team_earn_rolling, "Diff", 30)
            df_team_earn_rolling_30.columns = ["Date", "Diff30"]
            df_team_earn_rolling_30 = df_team_earn_rolling_30.merge(df_team_earn_rolling, on=["Date"])
            df_team_earn_rolling_365 = rollingAverage(df_team_earn_rolling, "Diff", 365)
            df_team_earn_rolling_365.columns = ["Date", "Diff365"]
            df_team_earn_rolling_365 = df_team_earn_rolling_365.merge(df_team_earn_rolling_30, on=["Date"])
            df_team_earn_rolling_total = df_team_earn_rolling_365
            df_team_earn_rolling_total.rename(
                columns={
                    "Diff": "Rolling Weekly Average",
                    "Diff30": "Rolling Monthly Average",
                    "Diff365": "Rolling Yearly Average",
                },
                inplace=True,
            )
            delta("Team Earning Rolling")
            # Comparing normalized worktime with normalized income
            df_comparison = df_team_earn_rolling_total.merge(df_team_normalised, how="inner", on="Date")
            delta("Comparison")

# =========================================================
# Figure: Comparing normalized worktime with normalized income
# =========================================================


def figureEarningsVersusWorkload(user_data):
    figure = px.scatter(height=600)

    figure.add_trace(
        go.Scatter(
            x=user_data["%-billable"],
            y=user_data["Rolling Weekly Average"],
            mode="markers",
            line=go.scatter.Line(color="darkgreen"),
            name="Weekly",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=user_data["%-billable30"],
            y=user_data["Rolling Monthly Average"],
            mode="markers",
            line=go.scatter.Line(color="salmon"),
            name="Monthly",
        )
    )
    figure.update_layout(xaxis_title="Billable fraction [%]", yaxis_title="Income / Cost")
    figure.update_layout(legend=dict(title="", orientation="v", y=0.99, x=0.01, font_size=16))
    return figure


# =========================================================
# Figure: Normalised time (individual)
# =========================================================


def figureNormalisedIndividual(user_data):
    figure = px.scatter(
        user_data[user_data["Date"] > ROLLING_DATE],
        x="Date",
        y=["%-billable", "%-internal"],
        facet_col="User",
        facet_col_wrap=2,
        color_discrete_sequence=["#8FBC8F", "#FF7F50"],
        height=1200,
    )
    figure.update_layout(title="Normalised data, rolling 7 days", yaxis_title="Work time [%]")
    return figure


# =========================================================
# Figure: Normalised time (team)
# =========================================================


def figureNormalisedTeam(team_data, last_date):
    figure = px.scatter(
        team_data.rename(
            columns={
                "%-billable": "Weekly Billable",
                "%-internal": "Weekly Internal",
                "%-billable30": "Monthly Billable",
                "%-internal30": "Monthly Internal",
            }
        ),
        x="Date",
        y=["Weekly Billable", "Weekly Internal", "Monthly Billable", "Monthly Internal"],
        color_discrete_sequence=["#8FBC8F", "#FF7F50", "#006400", "#A52A2A"],
        height=800,
    )
    figure.update_layout(title="Normalised team data", yaxis_title="Work time [%]")
    figure.update_layout(
        xaxis_rangeslider_visible=True,
        xaxis_range=[ROLLING_DATE, str(date.today())],
    )
    figure.add_vrect(
        x0=last_date,
        x1=max(team_data["Date"]),
        annotation_text="Incomplete reported data ᐅ",
        annotation_position="bottom left",
        fillcolor="darkred",
        opacity=0.10,
        line_width=0,
    )
    figure.update_layout(
        legend=dict(title="Rolling fractions", orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.75)
    )
    figure.add_hline(y=50, fillcolor="darkslategrey")

    return figure


# =========================================================
# Figure: Rolling income (individual)
# =========================================================


def figureRollingIncomeIndividual(df_user_income_rolling):
    figure = px.scatter(
        df_user_income_rolling[df_user_income_rolling["Date"] > ROLLING_DATE],
        x="Date",
        y="Income",
        facet_col="User",
        facet_col_wrap=3,
        height=800,
    )
    figure.update_layout(title="Rolling 7 days (income)")
    return figure


# =========================================================
# Figure: Rolling income (team)
# =========================================================


def figureRollingIncomeTeam(df_average_income_rolling_30, last_date):
    figure = px.scatter(
        df_average_income_rolling_30,
        x="Date",
        y=["Income", "Income30"],
        color_discrete_sequence=["#8FBC8F", "#006400"],
        height=600,
    )
    figure.update_layout(
        title="Rolling weekly income (average/person)",
        yaxis_title="Income [ € ]",
    )
    figure.update_layout(
        xaxis_rangeslider_visible=True,
        xaxis_range=[ROLLING_DATE, str(date.today())],
    )
    figure.update_layout(legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.75))
    figure.add_vrect(
        x0=last_date,
        x1=max(df_average_income_rolling_30["Date"]),
        annotation_text="Incomplete reported data ᐅ",
        annotation_position="bottom left",
        fillcolor="darkred",
        opacity=0.10,
        line_width=0,
    )
    return figure


# =========================================================
# Figure: Rolling total
# =========================================================


def figureRollingTotal(df_team_rolling_total, supplementary_data):
    df_raw_costs = supplementary_data.raw_costs
    figure = px.scatter(
        df_team_rolling_total,
        x="Date",
        y=["Income", "Income30"],
        color_discrete_sequence=["#B6B6B6", "#81C784"],
        height=600,
    )
    if not df_raw_costs.empty:
        figure.add_trace(
            go.Scatter(
                x=df_raw_costs["Month"],
                y=df_raw_costs["WeeklyExtCost"],
                mode="lines",
                line=go.scatter.Line(color="salmon"),
                fill="tozeroy",
                fillcolor="rgba(250,128,114,0.1)",
                name="Costs",
            )
        )
    figure.update_layout(
        title="Rolling weekly income (total)",
        yaxis_title="Income [ € ]",
    )
    figure.update_layout(legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.75))
    uncertain_area = supplementary_data.costs[supplementary_data.costs["Real_income"] == 0]
    figure.add_vrect(
        x0=min(uncertain_area["Date"]),
        x1=max(uncertain_area["Date"]) + pd.Timedelta(1, "D"),
        annotation_text="Uncertain ᐅ",
        annotation_position="bottom left",
        fillcolor="grey",
        opacity=0.15,
        line_width=0,
    )
    return figure


# =========================================================
# Figure: Financial plots
# =========================================================


def figureFinancialTotal(supplementary_data, year=None):
    figure = px.scatter(height=600)
    monthly_result = supplementary_data.raw_costs[supplementary_data.raw_costs["Real_income"] != 0]
    if not year is None:
        monthly_result = monthly_result[monthly_result["Year"] == str(year)]
    else:
        monthly_result = monthly_result.tail(6)

    figure.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=monthly_result["Real_income"],
            mode="lines",
            line=go.scatter.Line(color="#0F5567"),
            fill="tozeroy",
            fillcolor="rgba(15,85,103,0.1)",
            name="Income",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=-monthly_result["External_cost"],
            mode="lines",
            line=go.scatter.Line(color="#F0AA98"),
            fill="tozeroy",
            fillcolor="rgba(240,170,152,0.1)",
            name="Costs",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=monthly_result["Real_income"] - monthly_result["External_cost"],
            mode="lines",
            line=go.scatter.Line(color="#C4C4C4"),
            fill="tozeroy",
            fillcolor="rgba(196,196,196,0.5)",
            name="Result",
        )
    )

    monthly_result = monthly_result[monthly_result["Month"].dt.day == 1]
    monthly_result["Month"] = monthly_result["Month"] + pd.DateOffset(months=1) - pd.Timedelta("1 day")
    monthly_sum_cost = monthly_result.rolling(12, min_periods=1)["External_cost"].sum()
    monthly_sum_in = monthly_result.rolling(12, min_periods=1)["Real_income"].sum()
    monthly_result["Result"] = monthly_sum_in - monthly_sum_cost
    monthly_result["Name"] = monthly_result["Month"].dt.strftime("%Y-%m-01")
    logging.debug("%s", monthly_result)

    starting_bank = monthly_result["Starting_amount"].values[:1][0]
    if starting_bank != 0:
        monthly_result["First"] = pd.to_datetime(monthly_result["Name"])
        figure.add_trace(
            go.Scatter(
                x=monthly_result["First"],
                y=monthly_result["Starting_amount"],
                mode="lines+markers",
                line=go.scatter.Line(color="Green"),
                name="Bank",
            )
        )

    figure.add_trace(
        go.Scatter(
            x=monthly_result["Month"],
            y=monthly_result["Result"],
            mode="lines+markers",
            line=go.scatter.Line(color="black"),
            name="Cumulative result",
        )
    )
    if year is None:
        title = "last 3 months"
    else:
        title = year

    figure.update_layout(title=f"Financial numbers for {title}", yaxis_title="Income/Cost/Result [ € ]", hovermode="x")
    figure.update_layout(
        legend=dict(title="Monthly", orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.75)
    )

    return figure


# =========================================================
# Figure: Spent time on; billable/verifriday/other
# =========================================================


# Requires config: rates
def figureSpentTimePercentage(tempo_data):
    df_by_group = tempo_data.byTimeType().sort_values("Group")
    figure = px.histogram(
        df_by_group[df_by_group["Date"] > ROLLING_DATE],
        x="Date",
        y="Time",
        color="Timetype",
        height=400,
        barnorm="percent",
    )
    figure.update_layout(bargap=0.1, xaxis_title="", yaxis_title="Fractions [%]")
    figure.update_layout(
        legend=dict(title="Project Key", orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font_size=16)
    )
    return figure


# =========================================================
# Figure: Allocations over time
# =========================================================
# Requires config: rates
def figureAllocations(allocation_data):
    allocation_data["Start"] = pd.to_datetime(allocation_data["Start"])
    allocation_data["Stop"] = pd.to_datetime(allocation_data["Stop"])
    allocation_data["Allocation"] = pd.to_numeric(allocation_data["Allocation"], errors="coerce")
    allocation_data = allocation_data[allocation_data["Stop"] >= ALLOCATION_START]
    allocation_data.loc[allocation_data["Start"] <= ALLOCATION_START, "Start"] = ALLOCATION_START

    # Create a list to store rows for each day
    rows = []

    for _, row in allocation_data.iterrows():
        user = row["User"]
        allocation = row["Allocation"]
        unconfirmed = row["Unconfirmed"]
        jira_id = row["JiraID"]

        # Generate a date range for each day in the specified range
        date_range = pd.date_range(start=row["Start"], end=row["Stop"], freq="D")

        # Create a row for each day
        for date in date_range:
            rows.append(
                {
                    "User": user,
                    "Date": date,
                    "Allocation": allocation,
                    "Unconfirmed": unconfirmed,
                    "JiraID": jira_id,
                }
            )

    # Create a new DataFrame to group by user and date to aggregate the data
    result_df = pd.DataFrame(rows)

    result_df = (
        result_df.groupby(["User", "Date"])
        .agg(
            {
                "Allocation": "sum",
                "Unconfirmed": "max",  # True if any day is True
                "JiraID": lambda x: ",".join(x.unique()),  # Concatenate JiraIDs
            }
        )
        .reset_index()
    )

    # Group by relevant columns and aggregate date ranges into timelines
    allocation_data = (
        result_df.groupby(["User", "Allocation", "Unconfirmed", "JiraID"])
        .agg(Start=("Date", "min"), Stop=("Date", "max"))
        .reset_index()
    )

    # Define a function to determine color based on conditions
    def determine_color(row):
        result = ""
        if row["Unconfirmed"]:
            if row["Allocation"] < 0.4:
                result = "Unconfirmed (< 40%)"
            elif row["Allocation"] > 0.8:
                result = "Unconfirmed (> 80%)"
            result = "Unconfirmed"
        elif "?" in row["JiraID"]:
            if row["Allocation"] < 0.4:
                result = "Missing Jira (< 40%)"
            elif row["Allocation"] > 0.8:
                result = "Missing Jira (> 80%)"
            result = "Missing Jira"
        elif row["Allocation"] < 0.4:
            result = "Less than 40%"
        elif row["Allocation"] > 0.8:
            result = "More than 80%"
        else:
            result = "OK"
        return result

    color_mapping = {
        "Unconfirmed": "red",
        "Unconfirmed (< 40%)": "lightred",
        "Unconfirmed (> 80%)": "darkred",
        "Missing Jira": "gray",
        "Missing Jira (< 40%)": "lightgray",
        "Missing Jira (> 80%)": "darkslategray",
        "OK": "#2FB115",
        "Less than 40%": "lightgreen",
        "More than 80%": "darkgreen",
    }

    # Apply the function to create a new 'Color' column
    allocation_data["Color"] = allocation_data.apply(determine_color, axis=1)

    # Create a Gantt chart
    figure = px.timeline(
        allocation_data,
        x_start="Start",
        x_end="Stop",
        y="User",
        color="Color",
        hover_data={"JiraID": True, "Allocation": ":.0%"},  # Format Allocation as percentage
        title="Allocations by user",
        color_discrete_map=color_mapping,  # Explicitly define color mapping
    )

    # Add vertical line for current date
    figure.add_shape(
        dict(
            type="line",
            x0=TODAY,
            x1=TODAY,
            y0=0,
            y1=1,
            yref="paper",
            line=dict(color="red", width=2),
        )
    )

    # Add text annotation above the red line
    figure.add_annotation(
        text="Today",
        x=TODAY,
        y=1.1,
        yref="paper",
        showarrow=False,
        font=dict(color="red"),
    )

    figure.update_xaxes(title_text="")
    figure.update_yaxes(title_text="User")
    figure.update_layout(
        legend=dict(title="", orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font_size=16)
    )

    return [figure]


# =========================================================
# Figure: Rolling Income vs. Cost
# =========================================================


def figureRollingEarnings(df_team_earn_rolling_total, supplementary_data, last_day=None):
    figure = px.scatter(
        df_team_earn_rolling_total.rename(
            columns={
                "Rolling Weekly Average": "Weekly",
                "Rolling Monthly Average": "Monthly",
                "Rolling Yearly Average": "Yearly",
            }
        ),
        x="Date",
        y=["Weekly", "Monthly", "Yearly"],
        color_discrete_sequence=["#909F90", "#9090B0", "#508050"],
        height=800,
    )
    figure.add_hline(y=1, fillcolor="indigo")
    figure.add_vrect(
        x0=max(df_team_earn_rolling_total["Date"]) - pd.Timedelta(365, "D"),
        x1=max(df_team_earn_rolling_total["Date"]),
        annotation_text="One Year",
        annotation_position="top left",
        fillcolor="green",
        opacity=0.05,
        line_width=0,
    )
    uncertain_area = supplementary_data.costs[supplementary_data.costs["Real_income"] == 0]
    figure.add_vrect(
        x0=min(uncertain_area["Date"]),
        x1=max(uncertain_area["Date"]) + pd.Timedelta(1, "D"),
        annotation_text="Uncertain ᐅ",
        annotation_position="bottom left",
        fillcolor="grey",
        opacity=0.15,
        line_width=0,
    )
    figure.add_vrect(
        x0=max(df_team_earn_rolling_total["Date"]) - pd.Timedelta(30, "D"),
        x1=max(df_team_earn_rolling_total["Date"]),
        annotation_text="30 days",
        annotation_position="top left",
        fillcolor="darkgreen",
        opacity=0.05,
        line_width=0,
    )
    figure.update_layout(title="Income normalized with cost", yaxis_title="Income / Cost", hovermode="x")
    figure.update_layout(
        legend=dict(title="Rolling Averages", orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.75)
    )
    figure.update_layout(
        xaxis_rangeslider_visible=True,
        xaxis_range=[ROLLING_DATE, str(date.today())],
    )
    if last_day is not None:
        figure.add_vline(
            x=last_day,
            fillcolor="indigo",
            line_dash="dot",
        )
        figure.add_annotation(
            text="Last fully reported day",
            x=last_day,
            xanchor="right",
            y=0.8,
            yref="paper",
            showarrow=True,
            font=dict(color="indigo"),
        )

    return figure


# =========================================================
# Figure: Projects
# =========================================================
def figureProjectsIndividual(grouped_data):
    figure = px.histogram(
        grouped_data,
        x="Date",
        y="Time",
        color="Group",
        facet_col="User",
        facet_col_wrap=3,
        height=800,
    )
    figure.update_layout(bargap=0.1, xaxis_title="", yaxis_title="Time [h]", showlegend=False)

    return figure


def figureProjects(tempo_data):
    df_by_group = tempo_data.byGroup().sort_values("Group")
    df_by_group = df_by_group[df_by_group["Date"] > ROLLING_DATE]
    figure = px.histogram(df_by_group, x="Date", y="Time", color="Group", height=600)
    figure.update_layout(bargap=0.1, xaxis_title="", yaxis_title="Time [h]")
    figure.update_layout(
        legend=dict(title="Project Key", orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5, font_size=16)
    )

    return [figure, figureProjectsIndividual(df_by_group)]


# =========================================================
# Figure: Billable time
# =========================================================
def figureBillableOneYear(tempo_data, this_year=True):
    if this_year:
        year_data = tempo_data.thisYear().sort_values("Key")
        year = tempo_data.this_year
    else:
        year_data = tempo_data.lastYear().sort_values("Key")
        year = tempo_data.last_year

    figure = px.histogram(
        year_data,
        x="User",
        y="Billable",
        color="Key",
        height=600,
        title=f"Billable entries for {year}",
    )
    figure.update_xaxes(categoryorder="total ascending")
    figure.update_layout(yaxis_title="Billable entries [h]")

    return figure


def figureBillable(tempo_data):
    return [figureBillableOneYear(tempo_data), figureBillableOneYear(tempo_data, False)]


# =========================================================
# Figure: Internal time
# =========================================================


def figureInternalOneYear(tempo_data, this_year=True):
    if this_year:
        year_data = tempo_data.thisYear().sort_values("Key")
        year = tempo_data.this_year
    else:
        year_data = tempo_data.lastYear().sort_values("Key")
        year = tempo_data.last_year

    figure = px.histogram(
        year_data,
        x="User",
        y="Internal",
        color="Key",
        height=600,
        title=f"Internal entries for {year}",
    )
    figure.update_xaxes(categoryorder="total descending")
    figure.update_layout(yaxis_title="Internal entries [h]")

    return figure


def figureInternal(tempo_data):
    return [figureInternalOneYear(tempo_data), figureInternalOneYear(tempo_data, False)]


# =========================================================
# Figure: Paying projects
# =========================================================


def figurePayingProjects(tempo_data, year=None):
    figure = px.histogram(
        tempo_data.getYear(year).sort_values("Key"),
        x="Group",
        y="Income",
        color="User",
        height=600,
        title="",
    )
    figure.update_xaxes(categoryorder="total ascending")
    figure.update_layout(yaxis_title="Income [€]")
    figure.update_layout(
        legend=dict(title=f"{year}", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=-0.035)
    )

    return figure


# =========================================================
# Figure: Popular projects
# =========================================================


def figurePopularProjectsOneYear(tempo_data, this_year=True):
    if this_year:
        year_data = tempo_data.thisYear().sort_values("Key")
        year = tempo_data.this_year
    else:
        year_data = tempo_data.lastYear().sort_values("Key")
        year = tempo_data.last_year

    figure = px.histogram(
        year_data,
        x="Group",
        y="Time",
        color="User",
        height=600,
        title="",
    )
    figure.update_xaxes(categoryorder="total ascending")
    figure.update_layout(yaxis_title="Popular project entries [h]")
    figure.update_layout(
        legend=dict(title=f"{year}", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=-0.035)
    )

    return figure


def figurePopularProjects(tempo_data):
    return [figurePopularProjectsOneYear(tempo_data), figurePopularProjectsOneYear(tempo_data, False)]


# =========================================================
# Figure: Egg baskets
# -------------------
# Two variants
# - Sum of Income (Euro) if rates data exists
# - Sum of billable time otherwise
# =========================================================


# support function for the egg baskets
def crewCost(crew_data):
    if not crew_data.empty:
        crew_cost = crew_data
        #  6 weeks vacay
        crew_cost["My Cost"] = crew_cost["Total cost"] * (52 / 44)
        # select the part that do internal projects
        staff_cost = crew_cost.loc[crew_cost["Role"] == "Staff"]
        # keep only the consultants
        crew_cost = crew_cost.loc[crew_cost["Role"] == "Consultant"]
        shared_staff_cost = staff_cost["My Cost"].sum() / crew_cost.index.size
        crew_cost["My Share"] = crew_cost["My Cost"] + shared_staff_cost
        crew_cost["Sustainable"] = crew_cost["My Share"] * 1.1
    else:
        crew_cost = pd.DataFrame()

    return crew_cost


def figureEggBaskets(tempo_data, supplementary_data, crew_data):
    eggs_days_ago = 90
    if supplementary_data.rates.empty:
        yAxisTitle = "Sum of billable time"
        figure = px.histogram(tempo_data.byTotalGroup(eggs_days_ago), x="User", y="Billable", color="Group")
        figure.update_xaxes(categoryorder="total ascending")
        figure.update_layout(
            title="Sum of billable time (" + str(eggs_days_ago) + " days back)",
        )
    else:
        if not crew_data.empty:
            crew_cost = crewCost(crew_data)
            basket_data = tempo_data.byEggBaskets().merge(crew_cost, on="User", validate="many_to_one")
            basket_data = basket_data.sort_values(by=["TimeBasket", "Sustainable"])
        else:
            basket_data = tempo_data.byEggBaskets()

        yAxisTitle = "Sum of Income [ € ]"
        figure = px.bar(
            basket_data,
            x="User",
            y="Income",
            color="Group",
            facet_col="TimeBasket",
            facet_col_wrap=3,
            category_orders={"TimeBasket": ["60-90 days ago", "30-60 days ago", "0-30 days ago"]},
        )
        if not crew_data.empty:
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Cost"],
                name="My Cost",
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
                row=1,
                col=1,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Cost"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
                showlegend=False,
                row=1,
                col=2,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Cost"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
                showlegend=False,
                row=1,
                col=3,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Share"],
                name="Break Even",
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
                row=1,
                col=1,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Share"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
                showlegend=False,
                row=1,
                col=2,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Share"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
                showlegend=False,
                row=1,
                col=3,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["Sustainable"],
                name="Sustainable",
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
                row=1,
                col=1,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["Sustainable"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
                showlegend=False,
                row=1,
                col=2,
            )
            figure.add_scatter(
                x=basket_data["User"],
                y=basket_data["Sustainable"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
                showlegend=False,
                row=1,
                col=3,
            )
        figure.update_layout(
            title="Eggs to share (" + str(eggs_days_ago) + " days back)",
        )
    figure.update_layout(
        height=600,
        yaxis_title=yAxisTitle,
        bargap=0.1,
    )

    return figure


def figureMinumumRates(crew_data):
    if not crew_data.empty:
        crew_cost = crewCost(crew_data.sort_values(by="Total cost"))

        crew_cost["Cost Rate"] = crew_cost["My Cost"] * (12 / 52) / (crew_cost["Hours"] * 4)
        crew_cost["Share Rate"] = crew_cost["My Share"] * (12 / 52) / (crew_cost["Hours"] * 4)
        crew_cost["Sust Rate"] = crew_cost["Sustainable"] * (12 / 52) / (crew_cost["Hours"] * 4)

        figure = px.scatter()

        figure.add_scatter(
            x=crew_cost["User"],
            y=crew_cost["Sust Rate"],
            name="Sustainable",
            mode="lines+markers",
            line=dict(color="DarkGreen", dash="dot"),
            marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
        )
        figure.add_scatter(
            x=crew_cost["User"],
            y=crew_cost["Share Rate"],
            name="Break even",
            mode="lines+markers",
            line=dict(color="DarkRed", dash="dot"),
            marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
        )
        figure.add_scatter(
            x=crew_cost["User"],
            y=crew_cost["Cost Rate"],
            name="Salary",
            mode="lines+markers",
            line=dict(color="Black", dash="dot"),
            marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
        )
        figure.update_traces(hovertemplate="EUR: %{y:.0f}")
        figure.update_layout(
            title="Minimum rates (assuming 80% billable)", yaxis_title="Hourly rates [€]", hovermode="x"
        )
        figure.update_layout(legend=dict(title="", orientation="v", y=0.99, x=0.01, font_size=16))
    else:
        figure = px.scatter()

    return figure


def sustainableHours(crew_data):
    hours_df = pd.DataFrame()

    if not crew_data.empty:
        crew_cost = crewCost(crew_data.sort_values(by="Total cost", ascending=False))

        hours_df = hours_df.assign(Rate=lambda x: range(75, 175, 5))
        for _, row in crew_cost.iterrows():
            hours_df[row["User"]] = row["Sustainable"] * (12 / 52) / hours_df["Rate"]

        hours_df.set_index("Rate", inplace=True)

        figure = px.scatter(hours_df, color_discrete_sequence=px.colors.qualitative.Antique)
        figure.update_traces(mode="lines+markers")
        figure.update_layout(
            height=600,
            title=f"Sustainable Working Hours (weekly) <br> 1 EUR = {EUR2SEK} SEK",
            xaxis_title="Rate [€]",
            yaxis_title="Hours per week",
            legend_title_text="",
        )
        figure.update_traces(hovertemplate="Hours %{y:.1f} Rate: %{x:.0f} €")

        figure.update_xaxes(showspikes=True)
        figure.update_yaxes(showspikes=True)
        figure.update_layout(legend=dict(title="", orientation="v", y=0.99, xanchor="right", x=0.99, font_size=16))

    else:
        figure = px.scatter()

    return figure


# =========================================================
# Base rendering (only requires TEMPO_KEY)
# =========================================================

delta("Starting Rendering")
main_list = []
main_list.append(figureEggBaskets(tempo, supplementary, crew_df))
main_list.append(table_working_hours)
if not supplementary.rates.empty:
    main_list.append(table_missing_rates)

# Allocations
# Requires Notion Allocations DB
if not allocations_df.empty:
    [figure_allocations] = figureAllocations(allocations_df)
    main_list.append(figure_allocations)
delta("Allocations building")

tab_children = [dcc.Tab(label="Main", value="start_page")]
figure_tabs = {"start_page": ("Main", main_list)}

if SHOWTAB_PROJECTS:
    tab_children.append(dcc.Tab(label="Time spent on...", value="projects"))
    figures_project = figureProjects(tempo)
    figure_tabs["projects"] = ("What we work on", figures_project)
if SHOWTAB_BILLABLE:
    tab_children.append(dcc.Tab(label="Billable", value="billable"))
    figure_tabs["billable"] = ("Billable work", figureBillable(tempo))
if SHOWTAB_INTERNAL:
    tab_children.append(dcc.Tab(label="Internal", value="internal"))
    figure_tabs["internal"] = ("Internal work", figureInternal(tempo))
if SHOWTAB_POPULAR_PROJECTS:
    tab_children.append(dcc.Tab(label="Popular projects", value="popular_projects"))
    figure_tabs["popular_projects"] = ("Popular projects", figurePopularProjects(tempo))
if SHOWTAB_PAYING_PROJECTS:
    if "Real_income" in supplementary.costs:
        max_year = int(supplementary.raw_costs[supplementary.raw_costs["Real_income"] != 0]["Year"].max())
        figures = [figurePayingProjects(tempo, year) for year in range(START_DATE.year, max_year + 1)]
        figure_tabs["paying_projects"] = ("Paying projects", figures[::-1])
        tab_children.append(dcc.Tab(label="Paying projects", value="paying_projects"))


delta("Base Rendering")

# =========================================================
# Dynamic addition of content
# =========================================================

# ---------------------------------------------------------
# Allocations
# Requires Notion Allocations DB
if not allocations_df.empty:
    # Update projects page
    (head, plots) = figure_tabs["projects"]
    plots.append(figure_allocations)
    figure_tabs["projects"] = (head, plots)

# ---------------------------------------------------------
# Time spent groupings
# Requires rates file
if not supplementary.rates.empty:
    figure_time_spent = figureSpentTimePercentage(tempo)
    # Update projects page
    (head, plots) = figure_tabs["projects"]
    plots.append(figure_time_spent)
    figure_tabs["projects"] = (head, plots)

# ---------------------------------------------------------
# Financial data
# Requires income and costs in config files
if "Real_income" in supplementary.costs:
    max_year = int(supplementary.raw_costs[supplementary.raw_costs["Real_income"] != 0]["Year"].max())

    figures = [figureFinancialTotal(supplementary, year) for year in range(START_DATE.year, max_year + 1)]

    # Add tabs
    if SHOWTAB_FINANCE:
        figure_tabs["finance"] = ("Finances (real numbers)", figures[::-1])
        tab_children.append(dcc.Tab(label="Finances", value="finance"))

# ---------------------------------------------------------
# Project rates
# Requires config: rates, workinghours and costs
if not (supplementary.rates.empty or supplementary.working_hours.empty):
    # Add tabs
    if SHOWTAB_RATES:
        figure_tabs["rates"] = ("Rates", [table_rates])
        tab_children.append(dcc.Tab(label="Rates", value="rates"))
    if SHOWTAB_ROLLING_INCOME:
        figure_tabs["rolling_income"] = (
            "Rolling income",
            [
                figureRollingTotal(df_team_rolling_total, supplementary),
                figureRollingIncomeTeam(df_average_income_rolling_30, last_reported),
                figureRollingIncomeIndividual(df_user_income_rolling),
            ],
        )
        tab_children.append(dcc.Tab(label="Income analysis", value="rolling_income"))
    if not supplementary.costs.empty:
        figure_rolling_earnings = figureRollingEarnings(df_team_earn_rolling_total, supplementary, last_reported)
        # Update main page
        (head, plots) = figure_tabs["start_page"]
        plots.insert(0, figure_rolling_earnings)
        plots.insert(0, figureFinancialTotal(supplementary))
        figure_tabs["start_page"] = (head, plots)


# ---------------------------------------------------------
# Normalised working time
# Requires config files: workinghours
if not supplementary.working_hours.empty:
    # Add tab
    if SHOWTAB_NORMALISED_WORKTIME:
        figure_tabs["normalised_worktime"] = (
            "Normalised Work Time",
            [figureNormalisedTeam(df_team_normalised, last_reported), figureNormalisedIndividual(df_user_normalised)],
        )
        tab_children.append(dcc.Tab(label="Normalised Work Time", value="normalised_worktime"))


# ---------------------------------------------------------
# Break even
# Requires config files: workinghours, rates, finances
if (
    not supplementary.working_hours.empty
    and not supplementary.rates.empty
    and not supplementary.costs.empty
    and not df_comparison.empty
):
    # Add tab
    if SHOWTAB_COMPARISON:
        figures = []
        figures.append(figureMinumumRates(crew_df))
        figures.append(sustainableHours(crew_df))
        figures.append(figureEarningsVersusWorkload(df_comparison))

        figure_tabs["comparison"] = (
            "Comparing workload with income",
            figures,
        )
        tab_children.append(dcc.Tab(label="Break even", value="comparison"))


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
    if SHOWTAB_OKR_FIG:
        figure_tabs["okr_fig"] = ("OKR", okr_figs_kr + okr_figs_ini)
        tab_children.append(dcc.Tab(label="OKR", value="okr_fig"))

    # Update main page with NOTION_OKR_LABELS
    if SHOWMAIN_OKR_FIG:
        (head, plots) = figure_tabs["start_page"]
        plots += okr_figs_kr
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
    delta(tab)
    (head, plots) = figure_tabs[tab]
    sections = [dcc.Graph(id="plot", figure=figure) for figure in plots]
    sections.insert(0, dcc.Markdown("### " + head))
    return html.Div(html.Section(children=sections))
