"""The figures module"""

import logging
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from metrics.tempo_config import EUR2DKK, EUR2SEK, ROLLING_DATE


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
# Figure: Normalised time (individual)
# =========================================================


def figureNormalisedIndividual(user_data):
    figure = px.scatter(
        user_data[user_data["Date"] > ROLLING_DATE],
        x="Date",
        y=["%-billable", "%-internal"],
        facet_col="User",
        facet_col_wrap=2,
        facet_row_spacing=0.03,
        color_discrete_sequence=["#8FBC8F", "#FF7F50"],
        height=1600,
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
        facet_col_wrap=2,
        facet_row_spacing=0.03,
        height=1600,
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


# =================================
# Figure: rates to EUR
# =================================
def figureRatesToEUR():
    """Simple plot to show € for rates in SEK and DKK"""
    df_rates = pd.DataFrame()
    df_rates["Rates"] = range(750, 1500, 25)
    df_rates["SEK"] = df_rates["Rates"] / EUR2SEK
    df_rates["DKK"] = df_rates["Rates"] / EUR2DKK

    figure = px.scatter(height=400)
    figure.add_scatter(
        x=df_rates["Rates"],
        y=df_rates["SEK"],
        name="SEK",
        mode="lines+markers",
        line=dict(color="DarkBlue", dash="dot"),
    )
    figure.add_scatter(
        x=df_rates["Rates"], y=df_rates["DKK"], name="DKK", mode="lines+markers", line=dict(color="crimson", dash="dot")
    )
    figure.update_traces(hovertemplate="EUR: %{y:.0f}, RATE: %{x:.0f}")
    figure.update_xaxes(showspikes=True)
    figure.update_yaxes(showspikes=True)
    figure.update_layout(
        title="Rate converter",
        yaxis_title="Rates [€]",
        xaxis_title="Hourly rates",
        legend=dict(title="", orientation="v", y=0.99, x=0.01, font_size=16),
    )

    return figure
