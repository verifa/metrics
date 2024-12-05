"""Tempo related functions and classes"""

import json
import logging
import os

import pandas as pd

from metrics.date_utils import splitMonthTable


class SupplementaryData:
    """SupplementaryData data class"""

    working_hours: pd.DataFrame
    costs: pd.DataFrame
    internal_keys: pd.DataFrame
    financials: pd.DataFrame

    def __init__(self, config_path: str, financials: pd.DataFrame, working_hours: pd.DataFrame, rates: pd.DataFrame) -> None:
        self.rates = rates
        self.working_hours = working_hours
        self.costs = pd.DataFrame()
        self.raw_costs = pd.DataFrame()
        self.padding = pd.DataFrame()
        self.internal_keys = pd.DataFrame()
        self.financials = financials
        self.supp_data = SupplementaryRatesData(config_path)

    def load(self, users: pd.Series) -> None:
        if self.working_hours.empty:
            logging.info("Notion working hours table does not exist")
        else:
            logging.debug(users)
            for index, row in self.working_hours.iterrows():
                not_matches = (users == row["User"]).value_counts().loc[False]
                if not_matches == users.count():
                    self.working_hours.drop(index=index, inplace=True)

        if self.financials.empty:
            logging.warning("Notion financial table does not exist")
        else:
            self.costs = self.financials
            self.raw_costs = splitMonthTable(self.costs)
            logging.debug("Raw costs\n%s", self.raw_costs)
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
            self.costs["External_cost"] = self.costs["External_cost"] / self.costs["days_in_month"]
            if "Real_income" in self.costs:
                self.costs["Real_income"] = self.costs["Real_income"] / self.costs["days_in_month"]
            self.costs["Date"] = self.costs.index
            self.costs = self.costs.drop("days_in_month", axis=1)
            self.costs = self.costs.drop("Month", axis=1)
            logging.info("Loaded financials")
            self.rates["User"] = [users.values.tolist() for _ in range(len(self.rates))]
            self.rates = self.rates.explode("User")
            exceptions = pd.json_normalize(rates_json_data, record_path="Exceptions")
            self.rates = self.rates.merge(exceptions, on=["Key", "User"], how="left")
            rcol = self.rates["Rate_y"].fillna(self.rates["Rate_x"])
            self.rates["Rate"] = rcol
            self.rates = self.rates.drop(columns=["Rate_x", "Rate_y"])
            self.rates = self.rates.astype({"Rate": "int"})
            # adds the internal keys
            self.internal_keys = pd.json_normalize(rates_json_data, record_path="Internal")


# @TODO: Needs refining, loaded twice. May be use static?
class SupplementaryRatesData:
    rates_path: str
    rates_json_data: dict

    def __init__(self, config_path: str):
        self.rates_path = config_path + "/rates/data.json"

    def load(self):
        if not os.path.exists(self.rates_path):
            logging.warning("Rates file path does not exist: %s", self.rates_path)
        else:
            with open(self.rates_path, "r", encoding="utf8") as rates_file:
                self.rates_json_data = json.load(rates_file)
            logging.info("Loaded %s", self.rates_path)
        return self.rates_json_data
