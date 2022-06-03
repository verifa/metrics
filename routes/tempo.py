"""Tempo related functions and classes"""
import json
import os
import sys
from datetime import date

import numpy
import pandas
from tempoapiclient import client as Client

from routes.date_utils import lookBack, weekdays


class SupplementaryData:
    """SupplementaryData data class"""

    working_hours: pandas.DataFrame
    rates: pandas.DataFrame

    def __init__(self, users: pandas.Series, working_hours_path: str = None, rates_path: str = None) -> None:
        # Read paths from environment if missing
        if working_hours_path is None or rates_path is None:
            config_path = os.environ.get("TEMPO_CONFIG_PATH") or "/tempo"
            working_hours_path = working_hours_path or (config_path + "/workinghours.json")
            rates_path = rates_path or (config_path + "/rates.json")

        if not os.path.exists(working_hours_path):
            sys.exit("Working hours file path does not exist: " + working_hours_path)
        if not os.path.exists(rates_path):
            sys.exit("Rates file path does not exist: " + rates_path)

        self.working_hours = pandas.read_json(working_hours_path)
        print("Loaded " + working_hours_path)

        rates_data = json.load(open(rates_path))
        self.rates = pandas.json_normalize(rates_data, record_path="Default")
        print("Loaded " + rates_path)

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

    def __init__(self, base_url: str = "https://api.tempo.io/core/3", tempo_key: str = None) -> None:
        tempo_key = tempo_key or os.environ.get("TEMPO_KEY")
        if tempo_key is None:
            sys.exit("Tempo key not provided or TEMPO_KEY not set")
        self.client = Client.Tempo(auth_token=tempo_key, base_url=base_url)
        self.raw = pandas.DataFrame()
        self.data = pandas.DataFrame()

    def load(self, from_date: str = "1970-01-01", to_date: str = str(date.today())):
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

    def getUsers(self):
        """returns list of users"""
        return self.data["User"].drop_duplicates()

    def byGroup(self):
        """returns aggregated time and billable time grouped by date, user and group"""
        return self.data.groupby(["Date", "User", "Group"], as_index=False)[["Time", "Billable"]].sum()

    def byTotalGroup(self, days_back):
        """returns aggregated billable time grouped by issue key group and user"""
        timed_data = self.data[self.data["Date"] > lookBack(days_back)]
        df = timed_data.groupby(["Group", "User"], as_index=False)[["Billable"]].sum()
        df["Billable"].replace(0, numpy.nan, inplace=True)
        df.dropna(subset=["Billable"], inplace=True)
        return df

    def uprate(self, rates):
        uprated = self.data.merge(rates, on=["Key", "User"], how="left")
        uprated["Rate"] = uprated.apply(lambda x: x["Rate"] / 10 if x["Currency"] == "SEK" else x["Rate"], axis=1)
        uprated["Income"] = uprated["Rate"] * uprated["Billable"]
        self.data = uprated

    def byEggBaskets(self):
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

    def byDay(self):
        """returns aggregated time and billable time grouped by date, user and issue key"""
        return self.data.groupby(["Date", "User", "Key"], as_index=False)[["Time", "Billable"]].sum()

    def byUser(self, working_hours=None):
        """returns aggregated time and billable time grouped by user"""
        user_data = self.data.groupby("User", as_index=False)[["Time", "Billable"]].sum()
        # Find the first time entry for each user
        user_first = self.data.groupby("User", as_index=False)["Date"].min()
        # Add a unique comumn name
        user_first.columns = ["User", "First"]
        # Convert fime stamp to just date
        user_first["First"] = [x.date() for x in user_first["First"]]
        # add the column to the user data
        user_data = pandas.merge(user_data, user_first, on="User")
        user_last = self.data.groupby("User", as_index=False)["Date"].max()
        user_last.columns = ["User", "Last"]
        user_last["Last"] = [x.date() for x in user_last["Last"]]
        user_data = pandas.merge(user_data, user_last, on="User")
        user_data["Days"] = [weekdays(f, t) for f, t in zip(user_data["First"], user_data["Last"])]
        if not working_hours.empty:
            tmp_data = pandas.merge(user_data, working_hours, on="User")
            user_data = tmp_data
            user_data["Expected"] = [d * d2 for d, d2 in zip(user_data["Daily"], user_data["Days"])]
            user_data["Delta"] = [t - e for t, e in zip(user_data["Time"], user_data["Expected"])]

        return user_data

    def ratesTable(self):
        rate_data = self.data[self.data["Billable"] > 0]
        rate_data = rate_data.groupby(["Key", "Rate"], dropna=False, as_index=False).agg(
            Hours=("Billable", numpy.sum), Users=("User", ", ".join)
        )
        rate_data["Rate"].replace(numpy.nan, "<b>nan</b>", inplace=True)
        rate_data["Users"] = rate_data["Users"].str.split(", ").map(set).str.join(", ")
        return rate_data.sort_values(by=["Key", "Rate", "Hours"], ascending=[True, True, False], na_position="first")

    def userRolling7(self, to_sum):
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        daily_sum = self.data.groupby(["Date", "User"], as_index=False)[to_sum].sum()
        rolling_sum_7d = daily_sum.set_index("Date").groupby(["User"], as_index=False).rolling("7d")[to_sum].sum()
        return rolling_sum_7d.reset_index(inplace=False)

    def teamRolling7(self, to_sum):
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        daily_sum = self.data.groupby(["Date"], as_index=False)[to_sum].sum()
        rolling_sum_7d = daily_sum.set_index("Date").rolling("7d")[to_sum].sum()
        return rolling_sum_7d.reset_index(inplace=False)
