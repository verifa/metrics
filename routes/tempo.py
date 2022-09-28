"""Tempo related functions and classes"""
import json
import logging
import os
import sys
from datetime import date

import numpy
import pandas
from tempoapiclient import client as Client

from routes.date_utils import lookBack, weekdays


class SupplementaryData:
    """SupplementaryData data class"""

    rates_path: str
    rates: pandas.DataFrame
    working_hours_path: str
    working_hours: pandas.DataFrame
    costs_path: str
    costs: pandas.DataFrame

    def __init__(self, config_path: str) -> None:
        self.working_hours_path = config_path + "/workinghours/data.json"
        self.rates_path = config_path + "/rates/data.json"
        self.costs_path = config_path + "/costs/data.json"
        self.rates = pandas.DataFrame()
        self.working_hours = pandas.DataFrame()
        self.costs = pandas.DataFrame()
        self.padding = pandas.DataFrame()

    def load(self, users: pandas.Series) -> None:
        if not os.path.exists(self.working_hours_path):
            logging.warning("Working hours file path does not exist: " + self.working_hours_path)
        else:
            self.working_hours = pandas.read_json(self.working_hours_path)
            logging.info("Loaded " + self.working_hours_path)

        if not os.path.exists(self.costs_path):
            logging.warning("Costs file path does not exist: " + self.costs_path)
        else:
            self.costs = pandas.read_json(self.costs_path)
            self.costs.index.name = "Month"
            self.costs.index = self.costs["Month"]
            self.costs.index = self.costs.index.map(str)
            self.costs.index = self.costs.index.str[0:4] + "-" + self.costs.index.str[-2:]
            self.costs.index = pandas.period_range(
                start=self.costs.index.values[0], periods=len(self.costs.index.values), freq="m"
            )
            self.costs = self.costs.resample("D").ffill()
            daily = self.costs.groupby(pandas.Grouper(freq="M")).count()
            daily = daily.iloc[:, 0]
            daily = daily.resample("D").ffill().rename("days_in_month")
            self.costs = self.costs.join(daily)
            self.costs["Cost"] = self.costs["Cost"] / self.costs["days_in_month"]
            self.costs["Date"] = self.costs.index
            self.costs = self.costs.drop("days_in_month", axis=1)
            self.costs = self.costs.drop("Month", axis=1)
            logging.info("Loaded " + self.costs_path)

        if not os.path.exists(self.rates_path):
            sys.exit("[WARNING] Rates file path does not exist: " + self.rates_path)
        else:
            rates_data = json.load(open(self.rates_path))
            self.rates = pandas.json_normalize(rates_data, record_path="Default")
            logging.info("Loaded " + self.rates_path)

            self.rates["User"] = [users.values.tolist() for _ in range(len(self.rates))]
            self.rates = self.rates.explode("User")
            exceptions = pandas.json_normalize(rates_data, record_path="Exceptions")
            self.rates = self.rates.merge(exceptions, on=["Key", "User"], how="left")
            rcol = self.rates["Rate_y"].fillna(self.rates["Rate_x"])
            self.rates["Rate"] = rcol
            self.rates = self.rates.drop(columns=["Rate_x", "Rate_y"])
            self.rates = self.rates.astype({"Rate": "int"})


class TempoData:
    """Tempo data class."""

    client: Client
    raw: pandas.DataFrame
    data: pandas.DataFrame
    padded_data: pandas.DataFrame
    this_year: int
    last_year: int

    def __init__(self, base_url: str = "https://api.tempo.io/core/3", tempo_key: str = None) -> None:
        tempo_key = tempo_key or os.environ.get("TEMPO_KEY")
        if tempo_key is None:
            sys.exit("Tempo key not provided or TEMPO_KEY not set")
        self.client = Client.Tempo(auth_token=tempo_key, base_url=base_url)
        self.raw = pandas.DataFrame()
        self.data = pandas.DataFrame()

    def load(self, from_date: str = "1970-01-01", to_date: str = str(date.today())) -> None:
        """Fetch and populate data from Tempo for the given date range"""
        logs = self.client.get_worklogs(dateFrom=from_date, dateTo=to_date)
        self.raw = pandas.json_normalize(logs)
        self.data = self.raw[["issue.key", "timeSpentSeconds", "billableSeconds", "startDate", "author.displayName"]]
        self.data.columns = ["Key", "Time", "Billable", "Date", "User"]
        df = pandas.DataFrame(self.data.loc[:, ("Key")].str.split("-", 1).tolist(), columns=["Group", "Number"])
        self.data.loc[:, ("Group")] = df["Group"]
        self.data.loc[:, ("Date")] = pandas.to_datetime(self.data.loc[:, ("Date")], format="%Y-%m-%d")
        self.data.loc[:, ("Time")] = self.data.loc[:, ("Time")] / 3600
        self.data.loc[:, ("Billable")] = self.data.loc[:, ("Billable")] / 3600
        self.data.loc[:, ("Internal")] = self.data.loc[:, ("Time")] - self.data.loc[:, ("Billable")]
        self.data.loc[:, ("Year")] = self.data.loc[:, ("Date")].dt.year
        self.this_year = self.data["Year"].unique().max()
        self.last_year = self.this_year - 1

    def injectRates(self, rates: pandas.DataFrame) -> None:
        """Modify data by merging in the given rates data"""
        uprated = self.data.merge(rates, on=["Key", "User"], how="left")
        uprated["Rate"] = uprated.apply(lambda x: x["Rate"] / 10 if x["Currency"] == "SEK" else x["Rate"], axis=1)
        uprated["Income"] = uprated["Rate"] * uprated["Billable"]
        self.data = uprated

    def getUsers(self) -> pandas.Series:
        """returns list of users"""
        return self.data["User"].drop_duplicates()

    def byGroup(self) -> pandas.DataFrame:
        """returns aggregated time and billable time grouped by date, user and group"""
        return self.data.groupby(["Date", "User", "Group"], as_index=False)[["Time", "Billable"]].sum()

    def byTotalGroup(self, days_back) -> pandas.DataFrame:
        """returns aggregated billable time grouped by issue key group and user"""
        timed_data = self.data[self.data["Date"] > lookBack(days_back)]
        df = timed_data.groupby(["Group", "User"], as_index=False)[["Billable"]].sum()
        df["Billable"].replace(0, numpy.nan, inplace=True)
        df.dropna(subset=["Billable"], inplace=True)
        return df

    def byEggBaskets(self) -> pandas.DataFrame:
        """returns aggregated billable income grouped by issue key group, user and time box (30, 60, 90)"""

        baskets = self.data
        baskets["TimeBasket"] = "0"
        baskets.loc[baskets["Date"] > lookBack(90), "TimeBasket"] = "60-90 days ago"
        baskets.loc[baskets["Date"] > lookBack(60), "TimeBasket"] = "30-60 days ago"
        baskets.loc[baskets["Date"] > lookBack(30), "TimeBasket"] = "0-30 days ago"
        baskets["TimeBasket"].replace("0", numpy.nan, inplace=True)
        baskets.dropna(subset=["TimeBasket"], inplace=True)
        df = baskets.groupby(["Group", "User", "TimeBasket"], as_index=False)[["Income"]].sum()
        df["Income"].replace(0, numpy.nan, inplace=True)
        df.dropna(subset=["Income"], inplace=True)
        return df

    def byDay(self) -> pandas.DataFrame:
        """returns aggregated time and billable time grouped by date, user and issue key"""
        return self.data.groupby(["Date", "User", "Key"], as_index=False)[["Time", "Billable"]].sum()

    def firstEntry(self, user, start) -> pandas.Timestamp:
        if start == "*":
            first = self.data[self.data["User"] == user]["Date"].min()
        else:
            first = start

        return pandas.Timestamp(first)

    def lastEntry(self, user, stop) -> pandas.Timestamp:
        if stop == "*":
            data = self.data[self.data["Date"] < pandas.to_datetime("today")]
            last = data[data["User"] == user]["Date"].max()
        else:
            last = stop

        return pandas.Timestamp(last)

    def totalHours(self, user, start, stop=None):
        data = self.data[self.data["User"] == user]
        data = data[data["Date"] >= pandas.to_datetime(start)]
        if stop is None:
            total = data[data["Date"] < pandas.to_datetime("today")]["Time"].sum()
        else:
            total = data[data["Date"] <= pandas.to_datetime(stop)]["Time"].sum()

        return total

    def byUser(self, working_hours: pandas.DataFrame) -> pandas.DataFrame:
        """returns aggregated time and billable time grouped by user"""
        user_data = pandas.DataFrame()
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
            user_data["Last 7"] = [
                self.totalHours(user, start, stop)
                for user, start, stop in zip(
                    user_data["User"], user_data["Last"] - pandas.to_timedelta("6day"), user_data["Last"]
                )
            ]
            user_data["Trend"] = [
                last_week - 5 * daily for daily, last_week in zip(user_data["Daily"], user_data["Last 7"])
            ]
            user_data = user_data.drop(["Start", "Stop"], axis="columns")
            logging.info("\n" + user_data.to_string())

        else:
            # Find the first time entry for each user
            user_first = self.data.groupby("User", as_index=False)["Date"].min()
            # Add a unique column name
            user_first.columns = ["User", "First"]
            # Convert fime stamp to just date
            user_first["First"] = [x.date() for x in user_first["First"]]
            # remove all user/dates that are older than First
            user_data = pandas.merge(self.data, user_first, on="User")
            user_data = user_data[user_data["Date"] >= user_data["First"]]
            # summarize time and billable
            user_data = user_data.groupby("User", as_index=False)[["Time", "Billable"]].sum()
            # add the column to the user data
            user_data = pandas.merge(user_data, user_first, on="User")
            # remove today
            user_last = self.data[self.data["Date"] < pandas.Timestamp("today").strftime("%b %d, %Y")]
            user_last = user_last.groupby("User", as_index=False)["Date"].max()
            user_last.columns = ["User", "Last"]
            user_last["Last"] = [x.date() for x in user_last["Last"]]
            user_data = pandas.merge(user_data, user_last, on="User")
            user_data["Days"] = [weekdays(f, t) for f, t in zip(user_data["First"], user_data["Last"])]

        return user_data

    def ratesTable(self) -> pandas.DataFrame:
        rate_data = self.data[self.data["Billable"] > 0]
        rate_data = rate_data.groupby(["Key", "Rate"], dropna=False, as_index=False).agg(
            Hours=("Billable", numpy.sum), Users=("User", ", ".join)
        )
        rate_data["Rate"].replace(numpy.nan, "<b>nan</b>", inplace=True)
        rate_data["Users"] = rate_data["Users"].str.split(", ").map(set).str.join(", ")
        return rate_data.sort_values(by=["Key", "Rate", "Hours"], ascending=[True, True, False], na_position="first")

    def padTheData(self, working_hours: pandas.DataFrame) -> None:
        """
        creates the self.padded_data padded with zero data
        for each User, an entry for the ZP group will be added for each date >= min(Date) && <= max(Date)
        Key: ZP-1, Time: 0, Billable: 0, Group: ZP, Internal: 0, Currency: EUR, Rate: 0, Income: 0
        """
        self.padded_data = self.data
        if not working_hours.empty:
            for index, row in working_hours.iterrows():
                df_user = pandas.DataFrame()
                user = row["User"]
                if row["Start"] == "*":
                    start = self.data[self.data["User"] == user]["Date"].min()
                else:
                    start = row["Start"]
                if row["Stop"] == "*":
                    stop = self.data[self.data["User"] == user]["Date"].max()
                else:
                    stop = row["Stop"]
                df_user["Date"] = pandas.date_range(start, stop)
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
                self.padded_data = pandas.concat([self.padded_data, df_user])
        else:
            for user in self.data["User"].unique():
                df_user = pandas.DataFrame()
                start = self.data[self.data["User"] == user]["Date"].min()
                stop = self.data[self.data["User"] == user]["Date"].max()
                logging.debug(user, start, stop)
                df_user["Date"] = pandas.date_range(start, stop)
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
                self.padded_data = pandas.concat([self.padded_data, df_user])

    def userRolling7(self, to_sum) -> pandas.DataFrame:
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        daily_sum = self.padded_data.groupby(["Date", "User"], as_index=False)[to_sum].sum()
        rolling_sum_7d = (
            daily_sum.set_index("Date").groupby(["User"], as_index=False).rolling("7d", min_periods=7)[to_sum].sum()
        )
        return rolling_sum_7d.reset_index(inplace=False)

    def teamRolling7(self, to_sum) -> pandas.DataFrame:
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        daily_sum = self.padded_data.groupby(["Date"], as_index=False)[to_sum].sum()
        rolling_sum_7d = daily_sum.set_index("Date").rolling("7d", min_periods=7)[to_sum].sum()
        return rolling_sum_7d.reset_index(inplace=False)

    def teamRolling7Relative(self, costs: pandas.Series) -> pandas.DataFrame:
        """returns rolling 7 day sums for Billable and non Billable time grouped by user, relative to the costs"""
        daily_sum = self.padded_data.groupby(["Date"], as_index=False)["Income"].sum()
        daily_cost = costs
        daily_cost["Date"] = daily_cost["Date"].astype("datetime64[M]")

        daily_relative = pandas.merge(daily_sum, daily_cost, on=["Date"], how="outer")
        daily_relative = daily_relative.dropna()

        rolling_sum_7d = pandas.DataFrame()
        rolling_sum_7d["sumIncome"] = daily_relative.set_index("Date").rolling("7d", min_periods=7)["Income"].sum()
        rolling_sum_7d["sumCost"] = daily_relative.set_index("Date").rolling("7d", min_periods=7)["Cost"].sum()

        rolling_sum_7d["Diff"] = rolling_sum_7d["sumIncome"] / rolling_sum_7d["sumCost"]
        return rolling_sum_7d.reset_index(inplace=False)

    def thisYear(self) -> pandas.DataFrame:
        """returns a dataFrame with entries for the current year"""
        return self.data[self.data["Year"] == float(self.this_year)]

    def lastYear(self) -> pandas.DataFrame:
        """returns a dataFrame with entries for the previous year"""
        return self.data[self.data["Year"] == float(self.last_year)]
