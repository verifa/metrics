"""System module."""
import logging
import os
from datetime import date, datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html

from metrics.date_utils import lastMonthDay, lookBack
from metrics.notion import OKR, Allocations, Crew, Financials, WorkingHours
from metrics.supplementary_data import SupplementaryData
from metrics.tempo_config import ROLLING_DATE, START_DATE, TODAY, YESTERDAY
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
    logging.warning(f"{TEMPO_LOG_LEVEL} is not a valid log level, using default: WARNING")

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


def normaliseUserRolling7(frame, working_hours):
    first_date = START_DATE
    last_date = TODAY
    result = frame
    result["Daily"] = float(TEMPO_DAILY_HOURS)
    if not working_hours.empty:
        for _, row in working_hours.iterrows():
            if row["Daily"] != float(TEMPO_DAILY_HOURS):
                logging.debug(row["User"], row["Daily"])
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
logging.info(f"Starting {start}")


def delta(txt):
    delta = datetime.now() - start
    logging.info(f"{delta} : {txt}")


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

data = TempoData()
data.load(from_date=START_DATE, to_date=YESTERDAY)
delta("TempoData")

supplementary_data = SupplementaryData(TEMPO_CONFIG_PATH, financials_df, working_hours_df)
supplementary_data.load(data.getUsers())
delta("Supplementary Data")

data.zeroOutBillableTime(supplementary_data.internal_keys)
delta("ZeroOutBillable")

if not supplementary_data.rates.empty:
    data.injectRates(supplementary_data.rates)
    delta("InjectRates")
    table_rates = data.ratesTable(tableHeight, COLOR_HEAD, COLOR_ONE)
    delta("Table Rates")
    table_missing_rates = data.missingRatesTable(tableHeight, COLOR_HEAD, COLOR_ONE)
    delta("Table Missing Rates")

if not supplementary_data.working_hours.empty:
    data.padTheData(supplementary_data.working_hours)
    delta("Data Padding")


# =========================================================
# Table: User working hours
# =========================================================


table_working_hours = data.tableByUser(supplementary_data.working_hours, tableHeight, COLOR_HEAD, COLOR_ONE)
delta("Table Working Hours")
last_reported = pd.to_datetime(min(data.byUser(supplementary_data.working_hours)["Last"]))
logging.info(f"Last common day: {last_reported}")

if not supplementary_data.working_hours.empty:
    df_user_time_rolling = data.userRolling7(["Billable", "Internal"])
    delta("User Time Rolling")
    df_user_normalised = normaliseUserRolling7(df_user_time_rolling, supplementary_data.working_hours)
    delta("User Normalised")
    df_team_normalised = normaliseTeamAverage(df_user_normalised)
    delta("Team Normalised")
    if not supplementary_data.rates.empty:
        df_user_income_rolling = data.userRolling7("Income")
        delta("User Income Rolling")
        # Average user data
        df_average_income_rolling_7 = teamRollingAverage7(df_user_income_rolling, "Income")
        df_average_income_rolling_30 = rollingAverage(df_average_income_rolling_7, "Income", 30)
        df_average_income_rolling_30.columns = ["Date", "Income30"]
        df_average_income_rolling_30 = df_average_income_rolling_30.merge(df_average_income_rolling_7, on=["Date"])
        delta("Average Income Rolling")
        # Team total data
        df_team_income_rolling = data.teamRolling7("Income")
        df_team_income_rolling_30 = rollingAverage(df_team_income_rolling, "Income", 30)
        df_team_income_rolling_30.columns = ["Date", "Income30"]
        df_team_income_rolling_30 = df_team_income_rolling_30.merge(df_team_income_rolling, on=["Date"])
        df_team_rolling_total = df_team_income_rolling_30
        delta("User Income Rolling")
        # data for rolling earnings
        if not supplementary_data.costs.empty:
            df_team_earn_rolling = data.teamRolling7Relative(supplementary_data.costs)
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
    figure_earnings_versus_workload = px.scatter(height=600)

    figure_earnings_versus_workload.add_trace(
        go.Scatter(
            x=user_data["%-billable"],
            y=user_data["Rolling Weekly Average"],
            mode="markers",
            line=go.scatter.Line(color="darkgreen"),
            name="Weekly",
        )
    )
    figure_earnings_versus_workload.add_trace(
        go.Scatter(
            x=user_data["%-billable30"],
            y=user_data["Rolling Monthly Average"],
            mode="markers",
            line=go.scatter.Line(color="salmon"),
            name="Monthly",
        )
    )
    figure_earnings_versus_workload.update_layout(xaxis_title="Billable fraction [%]", yaxis_title="Income / Cost")
    return figure_earnings_versus_workload


# =========================================================
# Figure: Normalised time (individual)
# =========================================================


def figureNormalisedIndividual(user_data):
    figure_normalised_individual = px.scatter(
        user_data[user_data["Date"] > ROLLING_DATE],
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


def figureNormalisedTeam(team_data, last_date):
    figure_normalised_team = px.scatter(
        team_data,
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
    figure_normalised_team.add_vrect(
        x0=last_date,
        x1=max(team_data["Date"]),
        annotation_text="Incomplete reported data ᐅ",
        annotation_position="bottom left",
        fillcolor="darkred",
        opacity=0.10,
        line_width=0,
    )

    return figure_normalised_team


# =========================================================
# Figure: Rolling income (individual)
# =========================================================


def figureRollingIncomeIndividual(df_user_income_rolling):
    figure_rolling_income_individual = px.scatter(
        df_user_income_rolling[df_user_income_rolling["Date"] > ROLLING_DATE],
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


def figureRollingIncomeTeam(df_average_income_rolling_30, last_date):
    figure_rolling_income_team = px.scatter(
        df_average_income_rolling_30,
        x="Date",
        y=["Income", "Income30"],
        color_discrete_sequence=["#8FBC8F", "#006400"],
        height=600,
    )
    figure_rolling_income_team.update_layout(
        title="Rolling income (average/person)",
        yaxis_title="Income (euro)",
    )
    figure_rolling_income_team.update_layout(
        xaxis_rangeslider_visible=True,
        xaxis_range=[ROLLING_DATE, str(date.today())],
    )
    figure_rolling_income_team.add_vrect(
        x0=last_date,
        x1=max(df_average_income_rolling_30["Date"]),
        annotation_text="Incomplete reported data ᐅ",
        annotation_position="bottom left",
        fillcolor="darkred",
        opacity=0.10,
        line_width=0,
    )
    return figure_rolling_income_team


# =========================================================
# Figure: Rolling total
# =========================================================


def figureRollingTotal(df_team_rolling_total, df_raw_costs):
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
                y=df_raw_costs["WeeklyExtCost"],
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


def figureFinancialTotal(year=None):
    figure_rolling_total = px.scatter(height=600)
    monthly_result = supplementary_data.raw_costs[supplementary_data.raw_costs["Real_income"] != 0]
    monthly_result = monthly_result[monthly_result["Year"] == str(year)]

    figure_rolling_total.add_trace(
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
    figure_rolling_total.add_trace(
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
    figure_rolling_total.add_trace(
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
    logging.debug(monthly_result)

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
        title=f"Financial numbers for {year}",
        yaxis_title="Income/Cost/Result (euro)",
    )
    return figure_rolling_total


# =========================================================
# Figure: Spent time on; billable/verifriday/other
# =========================================================


# Requires config: rates
def figureSpentTimePercentage(data):
    df_by_group = data.byTimeType().sort_values("Group")
    figure_projects_team = px.histogram(
        df_by_group[df_by_group["Date"] > ROLLING_DATE],
        x="Date",
        y="Time",
        color="Timetype",
        height=400,
        barnorm="percent",
    )
    figure_projects_team.update_layout(bargap=0.1)
    return figure_projects_team


# =========================================================
# Figure: Allocations over time
# =========================================================
# Requires config: rates
def figureAllocations(allocations_df):
    allocations_df["Start"] = pd.to_datetime(allocations_df["Start"])
    allocations_df["Stop"] = pd.to_datetime(allocations_df["Stop"])
    allocations_df["Allocation"] = pd.to_numeric(allocations_df["Allocation"], errors="coerce")
    allocations_df = allocations_df[allocations_df["Stop"] >= ROLLING_DATE]
    allocations_df.loc[allocations_df["Start"] <= ROLLING_DATE, "Start"] = ROLLING_DATE

    # Create a list to store rows for each day
    rows = []

    for _, row in allocations_df.iterrows():
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
    allocations_df = (
        result_df.groupby(["User", "Allocation", "Unconfirmed", "JiraID"])
        .agg(Start=("Date", "min"), Stop=("Date", "max"))
        .reset_index()
    )

    # Define a function to determine color based on conditions
    def determine_color(row):
        if row["Unconfirmed"]:
            if row["Allocation"] < 0.4:
                return "Unconfirmed (< 40%)"
            elif row["Allocation"] > 0.8:
                return "Unconfirmed (> 80%)"
            return "Unconfirmed"
        elif "?" in row["JiraID"]:
            if row["Allocation"] < 0.4:
                return "Missing Jira (< 40%)"
            elif row["Allocation"] > 0.8:
                return "Missing Jira (> 80%)"
            return "Missing Jira"
        elif row["Allocation"] < 0.4:
            return "Less than 40%"
        elif row["Allocation"] > 0.8:
            return "More than 80%"
        else:
            return "OK"

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
    allocations_df["Color"] = allocations_df.apply(determine_color, axis=1)

    # Create a Gantt chart
    figure_allocated = px.timeline(
        allocations_df,
        x_start="Start",
        x_end="Stop",
        y="User",
        color="Color",
        hover_data={"JiraID": True, "Allocation": ":.0%"},  # Format Allocation as percentage
        title="Allocations by user",
        color_discrete_map=color_mapping,  # Explicitly define color mapping
    )

    # Add vertical line for current date
    figure_allocated.add_shape(
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
    figure_allocated.add_annotation(
        text="Today",
        x=TODAY,
        y=1.1,
        yref="paper",
        showarrow=False,
        font=dict(color="red"),
    )

    figure_allocated.update_xaxes(title_text="Date")
    figure_allocated.update_yaxes(title_text="User")

    return [figure_allocated]


# =========================================================
# Figure: Remaining Runway
# =========================================================
# Requires config: rates
def figureRunway(
    tempo_data: TempoData, supplemental: SupplementaryData, crew_df: pd.DataFrame, allocations_df: pd.DataFrame
):
    start_date = pd.Timestamp(supplemental.financials["Month"][-5])
    invoiced_cutoff = start_date - pd.offsets.MonthBegin()

    current_amount = supplemental.financials["Starting_amount"][-5]
    monthly_salaries = crew_df["Total cost"].sum()

    flattened_df = pd.DataFrame(columns=["Date", "costs only", "incl. known", "incl. allocated"])
    flattened_df.loc[-1] = [lookBack(1, start_date), current_amount, current_amount, current_amount]
    flattened_df.index = flattened_df.index + 1

    max_enddate = pd.Timestamp(allocations_df["Stop"].max())

    # known costs
    for day in pd.date_range(start_date, max_enddate + pd.offsets.MonthBegin(), freq="M"):
        cost = monthly_salaries

        flattened_df.loc[-1] = [day, -cost, -cost, -cost]
        flattened_df.index = flattened_df.index + 1
        flattened_df.loc[-1] = [lookBack(1, day), 0, 0, 0]
        flattened_df.index = flattened_df.index + 1

    # hours worked
    total_known = 0
    daily_sum = tempo_data.data.groupby(["Date"], as_index=False)["Income"].sum()
    for _, row in daily_sum.iterrows():
        day = row["Date"]
        if day < invoiced_cutoff:
            continue
        day = (
            pd.Timestamp(day) + pd.offsets.MonthBegin() + pd.offsets.Week(2)
        )  # TODO: Better estimate of invoicing date
        known = row["Income"]
        total_known += known

        flattened_df.loc[-1] = [day, 0, known, 0]
        flattened_df.index = flattened_df.index + 1
        flattened_df.loc[-1] = [lookBack(1, day), 0, 0, 0]
        flattened_df.index = flattened_df.index + 1

    # hours allocated
    for _, row in allocations_df.iterrows():
        if row["Unconfirmed"]:
            continue
        user = row["User"]
        allocation = row["Allocation"]
        start = pd.Timestamp(row["Start"])
        stop = pd.Timestamp(row["Stop"])
        task_id = row["JiraID"]
        if stop != None and stop < start_date:
            continue
        if start == None or start < invoiced_cutoff:
            start = invoiced_cutoff

        if stop == None:
            stop = max_enddate

        # I'm sure there's a nice clever one-liner to do this. I'm apparently not that clever.
        rate = 0
        for _, raterow in supplemental.rates[lambda df: (df["Key"] == task_id) & (df["User"] == user)].iterrows():
            rate = raterow["Rate"] / (11.43 if raterow["Currency"] == "SEK" else 1)  # TODO: Constant or helper for SEK
            break

        prevm = start
        nextm = start + pd.offsets.MonthBegin()
        while nextm <= stop:
            invoice_date = nextm + pd.offsets.Week(2)  # TODO: Better estimate of invoicing date
            workdays = (
                len(pd.bdate_range(prevm, nextm)) - 3
            )  # Slightly conservative estimate, as holidays and sick days are not factored otherwise
            amount = allocation * workdays * 7.5 * rate
            flattened_df.loc[-1] = [invoice_date, 0, 0, amount]
            flattened_df.index = flattened_df.index + 1
            flattened_df.loc[-1] = [lookBack(1, invoice_date), 0, 0, 0]
            flattened_df.index = flattened_df.index + 1
            prevm = nextm
            nextm = nextm + pd.offsets.MonthBegin()

    flattened_df = flattened_df.groupby(["Date"], as_index=False).sum()
    flattened_df = flattened_df.sort_values(by=["Date"])

    flattened_df["cum costs only"] = flattened_df["costs only"].cumsum().round(4)
    flattened_df["cum known"] = flattened_df["incl. known"].cumsum().round(4)
    flattened_df["cum allocated"] = flattened_df["incl. allocated"].cumsum().round(4)

    figure = px.scatter(height=600)
    figure.add_trace(
        go.Scatter(
            x=flattened_df["Date"],
            y=flattened_df["cum costs only"],
            mode="lines",
            line=go.scatter.Line(color="salmon"),
            name="Costs Only (salaries)",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=flattened_df["Date"],
            y=flattened_df["cum known"],
            mode="lines",
            line=go.scatter.Line(color="darkgreen"),
            name="Billable",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=flattened_df["Date"],
            y=flattened_df["cum allocated"],
            mode="lines",
            line=go.scatter.Line(color="darkblue"),
            name="Allocations",
        )
    )

    figure.update_layout(
        title="Unclamped Runway",
    )

    clamped = go.Figure(figure)
    clamped.update_layout(
        title="Runway",
        yaxis_range=[0, current_amount + total_known * 1.2],
    )

    return [clamped, figure]


# =========================================================
# Figure: Rolling Income vs. Cost
# =========================================================


def figureRollingEarnings(df_team_earn_rolling_total):
    figure_rolling_earnings = px.scatter(
        df_team_earn_rolling_total,
        x="Date",
        y=["Rolling Weekly Average", "Rolling Monthly Average", "Rolling Yearly Average"],
        color_discrete_sequence=["#C8E6C9", "#77AEE0", "#1B5E20"],
        height=600,
    )
    figure_rolling_earnings.add_hline(y=1, fillcolor="indigo")
    figure_rolling_earnings.add_vrect(
        x0=max(df_team_earn_rolling_total["Date"]) - pd.Timedelta(365, "D"),
        x1=max(df_team_earn_rolling_total["Date"]),
        annotation_text="One Year",
        annotation_position="top left",
        fillcolor="green",
        opacity=0.05,
        line_width=0,
    )
    figure_rolling_earnings.add_vrect(
        x0=max(df_team_earn_rolling_total["Date"]) - pd.Timedelta(30, "D"),
        x1=max(df_team_earn_rolling_total["Date"]),
        annotation_text="30 days",
        annotation_position="top right",
        fillcolor="darkgreen",
        opacity=0.05,
        line_width=0,
    )
    uncertain_area = supplementary_data.costs[supplementary_data.costs["Real_income"] == 0]
    figure_rolling_earnings.add_vrect(
        x0=min(uncertain_area["Date"]),
        x1=min(uncertain_area["Date"]) + pd.Timedelta(1, "D"),
        annotation_text="Uncertain ᐅ",
        annotation_position="bottom left",
        fillcolor="red",
        opacity=0.55,
        line_width=0,
    )
    figure_rolling_earnings.update_layout(
        title="Income normalized with cost",
        yaxis_title="Income / Cost",
    )
    return figure_rolling_earnings


# =========================================================
# Figure: Projects
# =========================================================


def figureProjects(data):
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

    df_by_group = data.byGroup().sort_values("Group")
    figure_projects_team = px.histogram(
        df_by_group[df_by_group["Date"] > ROLLING_DATE], x="Date", y="Time", color="Group", height=600
    )
    figure_projects_team.update_layout(bargap=0.1)

    return [figure_projects_team, figure_projects_individual]


# =========================================================
# Figure: Billable time
# =========================================================


def figureBillable(data):
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

    return [figure_billable_this_year, figure_billable_last_year]


# =========================================================
# Figure: Internal time
# =========================================================


def figureInternal(data):
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

    return [figure_internal_this_year, figure_internal_last_year]


# =========================================================
# Figure: Paying projects
# =========================================================


def figurePayingProjects(data, year=None):
    figure_paying_projects_this_year = px.histogram(
        data.getYear(year).sort_values("Key"),
        x="Group",
        y="Income",
        color="User",
        height=600,
        title=f"Paying projects for {year}",
    )
    figure_paying_projects_this_year.update_xaxes(categoryorder="total ascending")
    figure_paying_projects_this_year.update_layout(yaxis_title="Income [€]")

    return figure_paying_projects_this_year


# =========================================================
# Figure: Popular projects
# =========================================================


def figurePopularProjects(data):
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

    return [figure_popular_projects_this_year, figure_popular_projects_last_year]


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


def figureEggBaskets(data, supplementary_data, crew_data):
    eggs_days_ago = 90
    if supplementary_data.rates.empty:
        yAxisTitle = "Sum of billable time"
        figure_eggbaskets = px.histogram(data.byTotalGroup(eggs_days_ago), x="User", y="Billable", color="Group")
        figure_eggbaskets.update_xaxes(categoryorder="total ascending")
        figure_eggbaskets.update_layout(
            title="Sum of billable time (" + str(eggs_days_ago) + " days back)",
        )
    else:
        if not crew_data.empty:
            crew_cost = crewCost(crew_data)
            basket_data = data.byEggBaskets().merge(crew_cost, on="User", validate="many_to_one")
            basket_data = basket_data.sort_values(by=["TimeBasket", "Sustainable"])
        else:
            basket_data = data.byEggBaskets()

        yAxisTitle = "Sum of Income (Euro)"
        figure_eggbaskets = px.bar(
            basket_data,
            x="User",
            y="Income",
            color="Group",
            facet_col="TimeBasket",
            facet_col_wrap=3,
            category_orders={"TimeBasket": ["60-90 days ago", "30-60 days ago", "0-30 days ago"]},
        )
        if not crew_data.empty:
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Cost"],
                name="My Cost",
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
                row=1,
                col=1,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Cost"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
                showlegend=False,
                row=1,
                col=2,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Cost"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
                showlegend=False,
                row=1,
                col=3,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Share"],
                name="Break Even",
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
                row=1,
                col=1,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Share"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
                showlegend=False,
                row=1,
                col=2,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["My Share"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
                showlegend=False,
                row=1,
                col=3,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["Sustainable"],
                name="Sustainable",
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
                row=1,
                col=1,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["Sustainable"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
                showlegend=False,
                row=1,
                col=2,
            )
            figure_eggbaskets.add_scatter(
                x=basket_data["User"],
                y=basket_data["Sustainable"],
                mode="markers",
                marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
                showlegend=False,
                row=1,
                col=3,
            )
        figure_eggbaskets.update_layout(
            title="Eggs to share (" + str(eggs_days_ago) + " days back)",
        )
    figure_eggbaskets.update_layout(
        height=600,
        yaxis_title=yAxisTitle,
        bargap=0.1,
    )

    return figure_eggbaskets


def figureMinumumRates(crew_data):
    if not crew_data.empty:
        crew_cost = crewCost(crew_data.sort_values(by="Total cost"))

        crew_cost["Cost Rate"] = crew_cost["My Cost"] * (12 / 52) / (crew_cost["Hours"] * 4)
        crew_cost["Share Rate"] = crew_cost["My Share"] * (12 / 52) / (crew_cost["Hours"] * 4)
        crew_cost["Sust Rate"] = crew_cost["Sustainable"] * (12 / 52) / (crew_cost["Hours"] * 4)

        figure_minimum_rates = px.scatter()

        figure_minimum_rates.add_scatter(
            x=crew_cost["User"],
            y=crew_cost["Sust Rate"],
            name="Sustainable",
            mode="lines+markers",
            line=dict(color="DarkGreen", dash="dot"),
            marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkGreen")),
        )
        figure_minimum_rates.add_scatter(
            x=crew_cost["User"],
            y=crew_cost["Share Rate"],
            name="Break even",
            mode="lines+markers",
            line=dict(color="DarkRed", dash="dot"),
            marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="DarkRed")),
        )
        figure_minimum_rates.add_scatter(
            x=crew_cost["User"],
            y=crew_cost["Cost Rate"],
            name="Salary",
            mode="lines+markers",
            line=dict(color="Black", dash="dot"),
            marker=dict(size=24, symbol="line-ew", line=dict(width=3, color="Black")),
        )
        figure_minimum_rates.update_traces(hovertemplate="EUR: %{y:.2f}")
        figure_minimum_rates.update_layout(
            title="Minimum rates (assuming 80% billable)", yaxis_title="Hourly rates [€]", hovermode="x"
        )
    else:
        figure_minimum_rates = px.scatter()

    return figure_minimum_rates


# =========================================================
# Base rendering (only requires TEMPO_KEY)
# =========================================================

delta("Starting Rendering")

main_list = [table_working_hours]
if not supplementary_data.rates.empty:
    main_list.append(table_missing_rates)
main_list.append(figureEggBaskets(data, supplementary_data, crew_df))

# Allocations
# Requires Notion Allocations DB
if not allocations_df.empty:
    [figure_allocations] = figureAllocations(allocations_df)
    main_list.append(figure_allocations)
delta("Allocations building")

# Runway
# Requires rates file, financials, crew, and allocations
if "Real_income" in supplementary_data.costs and not crew_df.empty and not allocations_df.empty:
    [figure_runway_clamped, figure_runway_unclamped] = figureRunway(data, supplementary_data, crew_df, allocations_df)
    main_list.append(figure_runway_clamped)
delta("Runway building")

tab_children = [dcc.Tab(label="Main", value="start_page")]
figure_tabs = {"start_page": ("Main", main_list)}

if SHOWTAB_PROJECTS:
    tab_children.append(dcc.Tab(label="Time spent on...", value="projects"))
    figures_project = figureProjects(data)
    figure_tabs["projects"] = ("What we work on", figures_project)
if SHOWTAB_BILLABLE:
    tab_children.append(dcc.Tab(label="Billable", value="billable"))
    figure_tabs["billable"] = ("Billable work", figureBillable(data))
if SHOWTAB_INTERNAL:
    tab_children.append(dcc.Tab(label="Internal", value="internal"))
    figure_tabs["internal"] = ("Internal work", figureInternal(data))
if SHOWTAB_POPULAR_PROJECTS:
    tab_children.append(dcc.Tab(label="Popular projects", value="popular_projects"))
    figure_tabs["popular_projects"] = ("Popular projects", figurePopularProjects(data))
if SHOWTAB_PAYING_PROJECTS:
    if "Real_income" in supplementary_data.costs:
        max_year = int(supplementary_data.raw_costs[supplementary_data.raw_costs["Real_income"] != 0]["Year"].max())
        figures = [figurePayingProjects(data, year) for year in range(START_DATE.year, max_year + 1)]
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
if not supplementary_data.rates.empty:
    figure_time_spent = figureSpentTimePercentage(data)
    # Update projects page
    (head, plots) = figure_tabs["projects"]
    plots.append(figure_time_spent)
    figure_tabs["projects"] = (head, plots)

# ---------------------------------------------------------
# Financial data
# Requires income and costs in config files
if "Real_income" in supplementary_data.costs:
    max_year = int(supplementary_data.raw_costs[supplementary_data.raw_costs["Real_income"] != 0]["Year"].max())

    figures = [figureFinancialTotal(year) for year in range(START_DATE.year, max_year + 1)]

    # Add tabs
    if SHOWTAB_FINANCE:
        figure_tabs["finance"] = ("Finances (real numbers)", figures[::-1])
        tab_children.append(dcc.Tab(label="Finances", value="finance"))

# ---------------------------------------------------------
# Project rates
# Requires config: rates, workinghours and costs
if not (supplementary_data.rates.empty or supplementary_data.working_hours.empty):
    # Add tabs
    if SHOWTAB_RATES:
        figure_tabs["rates"] = ("Rates", [table_rates])
        tab_children.append(dcc.Tab(label="Rates", value="rates"))
    if SHOWTAB_ROLLING_INCOME:
        figure_tabs["rolling_income"] = (
            "Rolling income",
            [
                figureRollingTotal(df_team_rolling_total, supplementary_data.raw_costs),
                figureRollingIncomeTeam(df_average_income_rolling_30, last_reported),
                figureRollingIncomeIndividual(df_user_income_rolling),
            ],
        )
        tab_children.append(dcc.Tab(label="Income analysis", value="rolling_income"))
    if not supplementary_data.costs.empty:
        figure_rolling_earnings = figureRollingEarnings(df_team_earn_rolling_total)
        # Update main page
        (head, plots) = figure_tabs["start_page"]
        plots.append(figure_rolling_earnings)
        figure_tabs["start_page"] = (head, plots)


# ---------------------------------------------------------
# Normalised working time
# Requires config files: workinghours
if not supplementary_data.working_hours.empty:
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
    not supplementary_data.working_hours.empty
    and not supplementary_data.rates.empty
    and not supplementary_data.costs.empty
    and not df_comparison.empty
):
    # Add tab
    if SHOWTAB_COMPARISON:
        figures = []
        figures.append(figureMinumumRates(crew_df))
        if "Real_income" in supplementary_data.costs and not crew_df.empty and not allocations_df.empty:
            figures.append(figure_runway_unclamped)
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
