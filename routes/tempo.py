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

    def byTotalGroup(self, daysBack):
        """returns aggregated billable time grouped by issue key group and user"""
        timedData = self.data[self.data["Date"] > lookBack(daysBack)]
        df = timedData.groupby(["Group", "User"], as_index=False)[["Billable"]].sum()
        df["Billable"].replace(0, numpy.nan, inplace=True)
        df.dropna(subset=["Billable"], inplace=True)
        return df

    def uprateWork(self, rates):
        upRated = self.data.merge(rates, on=["Key", "User"], how="left")
        upRated["Rate"] = upRated.apply(lambda x: x["Rate"] / 10 if x["Currency"] == "SEK" else x["Rate"], axis=1)
        upRated["Income"] = upRated["Rate"] * upRated["Billable"]
        self.data = upRated

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

    def byUser(self, workingHours=None):
        """returns aggregated time and billable time grouped by user"""
        userData = self.data.groupby("User", as_index=False)[["Time", "Billable"]].sum()
        # Find the first time entry for each user
        userFirst = self.data.groupby("User", as_index=False)["Date"].min()
        # Add a unique comumn name
        userFirst.columns = ["User", "First"]
        # Convert fime stamp to just date
        userFirst["First"] = [x.date() for x in userFirst["First"]]
        # add the column to the user data
        userData = pandas.merge(userData, userFirst, on="User")
        userLast = self.data.groupby("User", as_index=False)["Date"].max()
        userLast.columns = ["User", "Last"]
        userLast["Last"] = [x.date() for x in userLast["Last"]]
        userData = pandas.merge(userData, userLast, on="User")
        userData["Days"] = [weekdays(f, t) for f, t in zip(userData["First"], userData["Last"])]
        if not workingHours.empty:
            # print(workingHours)
            tmpData = pandas.merge(userData, workingHours, on="User")
            userData = tmpData
            userData["Expected"] = [d * d2 for d, d2 in zip(userData["Daily"], userData["Days"])]
            userData["Delta"] = [t - e for t, e in zip(userData["Time"], userData["Expected"])]

        return userData

    def ratesTable(self):
        rateData = self.data[self.data["Billable"] > 0]
        rateData = rateData.groupby(["Key", "Rate"], dropna=False, as_index=False).agg(
            Hours=("Billable", numpy.sum), Users=("User", ", ".join)
        )
        rateData["Rate"].replace(numpy.nan, "<b>nan</b>", inplace=True)
        rateData["Users"] = rateData["Users"].str.split(", ").map(set).str.join(", ")
        return rateData.sort_values(by=["Key", "Rate", "Hours"], ascending=[True, True, False], na_position="first")

    def userRolling7(self, tosum):
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        dailySum = self.data.groupby(["Date", "User"], as_index=False)[tosum].sum()
        rolling7Sum = dailySum.set_index("Date").groupby(["User"], as_index=False).rolling("7d")[tosum].sum()
        return rolling7Sum.reset_index(inplace=False)

    def teamRolling7(self, tosum):
        """returns rolling 7 day sums for Billable and non Billable time grouped by user"""
        dailySum = self.data.groupby(["Date"], as_index=False)[tosum].sum()
        rolling7Sum = dailySum.set_index("Date").rolling("7d")[tosum].sum()
        return rolling7Sum.reset_index(inplace=False)
