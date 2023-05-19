"""Tempo related functions and classes"""
import json
import logging
import os

import pandas as pd

from metrics.date_utils import splitMonthTable


class SupplementaryData:
    """SupplementaryData data class"""

    rates_path: str
    rates: pd.DataFrame
    working_hours: pd.DataFrame
    costs: pd.DataFrame
    internal_keys: pd.DataFrame
    financials: pd.DataFrame

    def __init__(self, config_path: str, financials: pd.DataFrame, working_hours: pd.DataFrame) -> None:
        self.rates_path = config_path + "/rates/data.json"
        self.rates = pd.DataFrame()
        self.working_hours = working_hours
        self.costs = pd.DataFrame()
        self.raw_costs = pd.DataFrame()
        self.padding = pd.DataFrame()
        self.internal_keys = pd.DataFrame()
        self.financials = financials

    def load(self, users: pd.Series) -> None:
        if self.working_hours.empty:
            logging.info("Notion working hours table does not exist")
        else:
            print(users)
            for index, row in self.working_hours.iterrows():
                not_matches = (users == row["User"]).value_counts().loc[False]
                if not_matches == users.count():
                    self.working_hours.drop(index=index, inplace=True)

        if self.financials.empty:
            logging.warning("Notion financial table does not exist")
        else:
            self.costs = self.financials
            self.raw_costs = splitMonthTable(self.costs)
            logging.debug(f"Raw costs\n{self.raw_costs}")
            self.costs.index.name = "Month"
            self.costs.index = self.costs["Month"]
            self.costs.index = self.costs.index.map(str)
            self.costs.index = self.costs.index.str[0:4] + "-" + self.costs.index.str[-2:]
            self.costs.index = pd.period_range(
                start=self.costs.index.values[0], periods=len(self.costs.index.values), freq="m"
            )
            self.costs = self.costs.resample("D").ffill()
            daily = self.costs.groupby(pd.Grouper(freq="M")).count()
            daily = daily.iloc[:, 0]
            daily = daily.resample("D").ffill().rename("days_in_month")
            self.costs = self.costs.join(daily)
            self.costs["Cost"] = self.costs["Cost"] / self.costs["days_in_month"]
            self.costs["External_cost"] = self.costs["External_cost"] / self.costs["days_in_month"]
            if "Real_income" in self.costs:
                self.costs["Real_income"] = self.costs["Real_income"] / self.costs["days_in_month"]
            self.costs["Date"] = self.costs.index
            self.costs = self.costs.drop("days_in_month", axis=1)
            self.costs = self.costs.drop("Month", axis=1)
            logging.info("Loaded financials")

        if not os.path.exists(self.rates_path):
            logging.warning("Rates file path does not exist: " + self.rates_path)
        else:
            rates_data = json.load(open(self.rates_path))
            self.rates = pd.json_normalize(rates_data, record_path="Default")
            logging.info("Loaded " + self.rates_path)

            self.rates["User"] = [users.values.tolist() for _ in range(len(self.rates))]
            self.rates = self.rates.explode("User")
            exceptions = pd.json_normalize(rates_data, record_path="Exceptions")
            self.rates = self.rates.merge(exceptions, on=["Key", "User"], how="left")
            rcol = self.rates["Rate_y"].fillna(self.rates["Rate_x"])
            self.rates["Rate"] = rcol
            self.rates = self.rates.drop(columns=["Rate_x", "Rate_y"])
            self.rates = self.rates.astype({"Rate": "int"})
            # adds the internal keys
            self.internal_keys = pd.json_normalize(rates_data, record_path="Internal")
