"""Tempo related functions and classes"""
import logging
import os
import sys
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from tempoapiclient import client as Client

from metrics.date_utils import lookBack, weekdays
from metrics.tempo_config import YESTERDAY


class TempoData:
    """Tempo data class."""

    client: Client.Tempo
    raw: pd.DataFrame
    data: pd.DataFrame
    padded_data: pd.DataFrame
    this_year: int
    last_year: int

    def __init__(self, base_url: str = "https://api.tempo.io/core/3", tempo_key: Optional[str] = None) -> None:
        tempo_key = tempo_key or os.environ.get("TEMPO_KEY")
        if tempo_key is None:
            sys.exit("Tempo key not provided or TEMPO_KEY not set")
        self.client = Client.Tempo(auth_token=tempo_key, base_url=base_url)
        self.raw = pd.DataFrame()
        self.data = pd.DataFrame()

    def load(self, from_date: str = "1970-01-01", to_date: str = str(date.today())) -> None:
        """Fetch and populate data from Tempo for the given date range"""
        logs = self.client.get_worklogs(dateFrom=from_date, dateTo=to_date)
        self.raw = pd.json_normalize(logs)
        self.data = self.raw[["issue.key", "timeSpentSeconds", "billableSeconds", "startDate", "author.displayName"]]
        self.data.columns = ["Key", "Time", "Billable", "Date", "User"]
        df = pd.DataFrame(self.data.loc[:, ("Key")].str.split("-", n=1).tolist(), columns=["Group", "Number"])
        self.data.loc[:, ("Group")] = df["Group"]
        self.data.loc[:, ("Date")] = pd.to_datetime(self.data.loc[:, ("Date")], format="%Y-%m-%d")
        self.data.loc[:, ("Time")] = self.data.loc[:, ("Time")] / 3600
        self.data.loc[:, ("Billable")] = self.data.loc[:, ("Billable")] / 3600
        self.data.loc[:, ("Internal")] = self.data.loc[:, ("Time")] - self.data.loc[:, ("Billable")]
        self.data.loc[:, ("Year")] = self.data.loc[:, ("Date")].dt.year
        self.this_year = self.data["Year"].unique().max()
        self.last_year = self.this_year - 1

    def injectRates(self, rates: pd.DataFrame) -> None:
        """Modify data by merging in the given rates data"""
        uprated = self.data.merge(rates, on=["Key", "User"], how="left")
        uprated["Rate"] = uprated.apply(lambda x: x["Rate"] / 11.43 if x["Currency"] == "SEK" else x["Rate"], axis=1)
        uprated["Income"] = uprated["Rate"] * uprated["Billable"]
        self.data = uprated

    def getUsers(self) -> pd.Series:
        """returns list of users"""
        return self.data["User"].drop_duplicates()

    def byGroup(self) -> pd.DataFrame:
        """returns aggregated time and billable time grouped by date, user and group"""
        return self.data.groupby(["Date", "User", "Group"], as_index=False)[["Time", "Billable"]].sum()

    def byTimeType(self) -> pd.DataFrame:
        """returns aggregated time and time type grouped by date, user and group"""
        newdata = self.data.copy()
        newdata["Timetype"] = pd.isna(newdata["Rate"])
        newdata["Timetype"] = ["Billable" if not (x) else "Non-billable" for x in newdata["Timetype"]]
        newdata["Timetype"] = [
            "VeriFriday" if x == "VF" else newdata["Timetype"][idx] for idx, x in enumerate(newdata["Group"])
        ]
        return newdata.groupby(["Date", "Timetype", "Group"], as_index=False)[["Time", "Timetype"]].sum()

    def byTotalGroup(self, days_back) -> pd.DataFrame:
        """returns aggregated billable time grouped by issue key group and user"""
        timed_data = self.data[self.data["Date"] > lookBack(days_back)]
        df = timed_data.groupby(["Group", "User"], as_index=False)[["Billable"]].sum()
        df["Billable"].replace(0, np.nan, inplace=True)
        df.dropna(subset=["Billable"], inplace=True)
        return df

    def byEggBaskets(self) -> pd.DataFrame:
        """returns aggregated billable income grouped by issue key group, user and time box (30, 60, 90)"""
        baskets = self.data.copy()
        baskets["TimeBasket"] = "0"
        baskets.loc[baskets["Date"] > lookBack(90), "TimeBasket"] = "60-90 days ago"
        baskets.loc[baskets["Date"] > lookBack(60), "TimeBasket"] = "30-60 days ago"
        baskets.loc[baskets["Date"] > lookBack(30), "TimeBasket"] = "0-30 days ago"
        baskets["TimeBasket"].replace("0", np.nan, inplace=True)
        baskets.dropna(subset=["TimeBasket"], inplace=True)
        df = baskets.groupby(["Group", "User", "TimeBasket"], as_index=False)[["Income"]].sum()
        df["Income"].replace(0, np.nan, inplace=True)
        df.dropna(subset=["Income"], inplace=True)
        return df

    def byDay(self) -> pd.DataFrame:
        """returns aggregated time and billable time grouped by date, user and issue key"""
        return self.data.groupby(["Date", "User", "Key"], as_index=False)[["Time", "Billable"]].sum()

    def firstEntry(self, user, start) -> pd.Timestamp:
        if start == "*":
            first = self.data[self.data["User"] == user]["Date"].min()
        else:
            first = start

        return pd.Timestamp(first)

    def lastEntry(self, user, stop) -> pd.Timestamp:
        if stop == "*":
            data = self.data[self.data["Date"] < pd.to_datetime("today")]
            last = data[data["User"] == user]["Date"].max()
        else:
            last = stop

        return pd.Timestamp(last)

    def totalHours(self, user, start, stop=None):
        data = self.data[self.data["User"] == user]
        data = data[data["Date"] >= pd.to_datetime(start)]
        if stop is None:
            total = data["Time"].sum()
        else:
            total = data[data["Date"] <= pd.to_datetime(stop)]["Time"].sum()

        return total

    def byUser(self, working_hours: pd.DataFrame) -> pd.DataFrame:
        """returns aggregated time and billable time grouped by user"""
        user_data = pd.DataFrame()
        if not working_hours.empty:
            user_data = working_hours[working_hours["Stop"] == "*"]
            user_data["Trend"] = 0
            user_data["First"] = [self.firstEntry(u, s).date() for u, s in zip(user_data["User"], user_data["Start"])]
            user_data["Last"] = [self.lastEntry(u, s).date() for u, s in zip(user_data["User"], user_data["Stop"])]
            user_data["Days"] = [weekdays(f, t) for f, t in zip(user_data["First"], user_data["Last"])]
            user_data["Expected"] = [days * daily for days, daily in zip(user_data["Days"], user_data["Daily"])]

            user_data["Total"] = [
                self.totalHours(user, start) for user, start in zip(user_data["User"], user_data["First"])
            ]
            user_data["Delta"] = user_data["Delta"] + [
                tot - exp for tot, exp in zip(user_data["Total"], user_data["Expected"])
            ]
            user_data["Last 7 days"] = [
                self.totalHours(user, start, stop)
                for user, start, stop in zip(
                    user_data["User"], user_data["Last"] - pd.to_timedelta("6day"), user_data["Last"]
                )
            ]
            user_data["Trend"] = [
                last_week - 5 * daily for daily, last_week in zip(user_data["Daily"], user_data["Last 7 days"])
            ]
            logging.info("\n" + user_data.to_string())
            user_data = user_data.drop(["Daily", "Start", "Stop", "First", "Days", "Expected", "Total"], axis="columns")

        else:
            # Find the first time entry for each user
            user_first = self.data.groupby("User", as_index=False)["Date"].min()
            # Add a unique column name
            user_first.columns = ["User", "First"]
            # Convert fime stamp to just date
            user_first["First"] = [x.date() for x in user_first["First"]]
            # remove all user/dates that are older than First
            user_data = pd.merge(self.data, user_first, on="User")
            user_data = user_data[user_data["Date"] >= user_data["First"]]
            # summarize time and billable
            user_data = user_data.groupby("User", as_index=False)[["Time", "Billable"]].sum()
            # add the column to the user data
            user_data = pd.merge(user_data, user_first, on="User")
            # remove today
            user_last = self.data[self.data["Date"] < pd.Timestamp("today").strftime("%b %d, %Y")]
            user_last = user_last.groupby("User", as_index=False)["Date"].max()
            user_last.columns = ["User", "Last"]
            user_last["Last"] = [x.date() for x in user_last["Last"]]
            user_data = pd.merge(user_data, user_last, on="User")
            user_data["Days"] = [weekdays(f, t) for f, t in zip(user_data["First"], user_data["Last"])]

        return user_data

    def tableByUser(
        self, working_hours, fnTableHeight=None, color_head="paleturquoise", color_cells="lavender"
    ) -> go.Figure:
        table_working_hours = self.byUser(working_hours).round(2)
        if not working_hours.empty:
            cell_values = [
                table_working_hours["User"],
                table_working_hours["Delta"],
                table_working_hours["Trend"],
                table_working_hours["Last"],
                table_working_hours["Last 7 days"],
            ]
        else:
            cell_values = [
                table_working_hours["User"],
                table_working_hours["Time"],
                table_working_hours["Billable"],
                table_working_hours["First"],
                table_working_hours["Last"],
                table_working_hours["Days"],
            ]

        fig = go.Figure(
            data=[
                go.Table(
                    header=dict(values=list(table_working_hours.columns), fill_color=color_head, align="left"),
                    cells=dict(
                        values=cell_values,
                        fill_color=color_cells,
                        align="left",
                    ),
                )
            ]
        )
        if fnTableHeight:
            fig.update_layout(height=fnTableHeight(table_working_hours))
        return fig

    def rawRatesTable(self) -> pd.DataFrame:
        rate_data = self.data[self.data["Billable"] > 0]
        rate_data = rate_data.groupby(["Key", "Rate"], dropna=False, as_index=False).agg(
            Hours=("Billable", np.sum), Users=("User", ", ".join)
        )
        rate_data["Rate"].replace(np.nan, "???", inplace=True)
        rate_data["Users"] = rate_data["Users"].str.split(", ").map(set).str.join(", ")
        return rate_data

    def ratesTable(self, fnTableHeight=None, color_head="paleturquoise", color_cells="lavender") -> go.Figure:
        rate_data = self.rawRatesTable()
        fig = go.Figure(
            data=[
                go.Table(
                    columnwidth=[50, 50, 50, 400],
                    header=dict(values=list(rate_data.columns), fill_color=color_head, align="left"),
                    cells=dict(
                        values=[rate_data["Key"], rate_data["Rate"], rate_data["Hours"], rate_data["Users"]],
                        fill_color=color_cells,
                        align="left",
                    ),
                )
            ]
        )
        fig.update_layout(title="Rates")
        if fnTableHeight:
            fig.update_layout(height=fnTableHeight(rate_data))
        return fig

    def missingRatesTable(self, fnTableHeight=None, color_head="paleturquoise", color_cells="lavender") -> go.Figure:
        rate_data = self.rawRatesTable()
        rate_data = rate_data[rate_data["Rate"] == "???"]
        fig = go.Figure(
            data=[
                go.Table(
                    columnwidth=[50, 50, 50, 400],
                    header=dict(values=list(rate_data.columns), fill_color=color_head, align="left"),
                    cells=dict(
                        values=[rate_data["Key"], rate_data["Rate"], rate_data["Hours"], rate_data["Users"]],
                        fill_color=color_cells,
                        align="left",
                    ),
                )
            ]
        )
        fig.update_layout(title="Missing Rates")
        if fnTableHeight:
            fig.update_layout(height=fnTableHeight(rate_data))
        return fig

    def padTheData(self, working_hours: pd.DataFrame) -> None:
        """
        creates the self.padded_data padded with zero data
        for each User, an entry for the ZP group will be added for each date >= min(Date) && <= max(Date)
        Key: ZP-1, Time: 0, Billable: 0, Group: ZP, Internal: 0, Currency: EUR, Rate: 0, Income: 0
        """
        self.padded_data = self.data
        if not working_hours.empty:
            for index, row in working_hours.iterrows():
                df_user = pd.DataFrame()
                user = row["User"]
                if row["Start"] == "*":
                    start = self.data[self.data["User"] == user]["Date"].min()
                else:
                    start = row["Start"]
                if row["Stop"] == "*":
                    stop = YESTERDAY
                else:
                    stop = row["Stop"]
                df_user["Date"] = pd.date_range(start, stop)
                df_user["User"] = user
                df_user["Key"] = "ZP-1"
                df_user["Time"] = 0.0
                df_user["Billable"] = 0.0
                df_user["Group"] = "ZP"
                df_user["Internal"] = 0.0
                df_user["Year"] = df_user.loc[:, ("Date")].dt.year
                df_user["Currency"] = "EUR"
                df_user["Rate"] = 0
                df_user["Income"] = 0
                self.padded_data = pd.concat([self.padded_data, df_user])
        else:
            for user in self.data["User"].unique():
                df_user = pd.DataFrame()
                start = self.data[self.data["User"] == user]["Date"].min()
                stop = self.data[self.data["User"] == user]["Date"].max()
                df_user["Date"] = pd.date_range(start, stop)
                df_user["User"] = user
                df_user["Key"] = "ZP-1"
                df_user["Time"] = 0.0
                df_user["Billable"] = 0.0
                df_user["Group"] = "ZP"
                df_user["Internal"] = 0.0
                df_user["Year"] = df_user.loc[:, ("Date")].dt.year
                df_user["Currency"] = "EUR"
                df_user["Rate"] = 0
                df_user["Income"] = 0
                self.padded_data = pd.concat([self.padded_data, df_user])

    def userRolling7(self, to_sum) -> pd.DataFrame:
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        daily_sum = self.padded_data.groupby(["Date", "User"], as_index=False)[to_sum].sum()
        rolling_sum_7d = (
            daily_sum.set_index("Date").groupby(["User"], as_index=False).rolling("7d", min_periods=7)[to_sum].sum()
        )
        return rolling_sum_7d.reset_index(inplace=False)

    def teamRolling7(self, to_sum) -> pd.DataFrame:
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        daily_sum = self.padded_data.groupby(["Date"], as_index=False)[to_sum].sum()
        rolling_sum_7d = daily_sum.set_index("Date").rolling("7d", min_periods=7)[to_sum].sum()
        return rolling_sum_7d.reset_index(inplace=False)

    def teamRolling7Relative(self, costs: pd.Series) -> pd.DataFrame:
        """returns rolling 7 day sums for Billable and non Billable time grouped by user, relative to the costs"""
        daily_sum = self.padded_data.groupby(["Date"], as_index=False)["Income"].sum()
        daily_cost = costs
        daily_cost["Date"] = daily_cost["Date"].astype("datetime64[M]")

        daily_relative = pd.merge(daily_sum, daily_cost, on=["Date"], how="outer")
        daily_relative = daily_relative.dropna()

        rolling_sum_7d = pd.DataFrame()
        rolling_sum_7d["sumIncome"] = daily_relative.set_index("Date").rolling("7d", min_periods=7)["Income"].sum()
        rolling_sum_7d["sumExtCost"] = daily_relative.set_index("Date").rolling("7d", min_periods=7)["External_cost"].sum()

        rolling_sum_7d["Diff"] = rolling_sum_7d["sumIncome"] / rolling_sum_7d["sumExtCost"]
        return rolling_sum_7d.reset_index(inplace=False)

    def thisYear(self) -> pd.DataFrame:
        """returns a dataFrame with entries for the current year"""
        return self.data[self.data["Year"] == float(self.this_year)]

    def lastYear(self) -> pd.DataFrame:
        """returns a dataFrame with entries for the previous year"""
        return self.data[self.data["Year"] == float(self.last_year)]

    def zeroOutBillableTime(self, keys: pd.DataFrame) -> None:
        """
        Sets billable time to zero (0) for internal project keys
        """
        if not keys.empty:
            for key in keys["Key"]:
                logging.debug("Internal Key: " + key)
                self.data.loc[self.data["Group"] == key, ("Billable")] = 0
                self.data.loc[self.data["Group"] == key, ("Internal")] = self.data[self.data["Group"] == key]["Time"]
