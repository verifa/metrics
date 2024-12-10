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
    financials: pd.DataFrame

    def __init__(
        self,
        financials: pd.DataFrame,
        working_hours: pd.DataFrame,
        default_rates: pd.DataFrame,
        exceptional_rates: pd.DataFrame,
    ) -> None:
        self.rates = default_rates
        self.working_hours = working_hours
        self.costs = pd.DataFrame()
        self.raw_costs = pd.DataFrame()
        self.padding = pd.DataFrame()
        self.internal_keys = pd.DataFrame()
        self.financials = financials
        self.exceptional_rates = exceptional_rates

    def load(self, users: pd.Series) -> None:
        if self.working_hours.empty:
            logging.info("Notion working hours table does not exist")
        else:
            logging.debug(users)
            logging.debug(self.working_hours)
            # Remove users who are not active (alumini)
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
            logging.debug("Modified costs%s", self.costs)
            logging.info("Loaded financials")
            self.rates["User"] = [users.values.tolist() for _ in range(len(self.rates))]
            self.rates = self.rates.explode("User")
            self.rates = self.rates.merge(self.exceptional_rates, on=["Key", "User"], how="left")
            rcol = self.rates["Rate_y"].fillna(self.rates["Rate_x"])
            self.rates["Rate"] = rcol
            self.rates = self.rates.drop(columns=["Rate_x", "Rate_y"])
            self.rates = self.rates.astype({"Rate": "int"})
            logging.debug("MOdified rates%s", self.rates)
