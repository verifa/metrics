import json
import os
import sys

import pandas


class TempoConfig:
    """TempoConfig data class"""
    workingHours : pandas.DataFrame
    rates : pandas.DataFrame

    def __init__(self, users: range = [], workingHoursPath: str = None, ratesPath: str = None) -> None:
        # Read paths from environments if missing
        if workingHoursPath is None or ratesPath is None:
            configPath = os.environ.get("TEMPO_CONFIG_PATH") or '/tempo'
            workingHoursPath = workingHoursPath or (configPath + "/workinghours.json")
            ratesPath = ratesPath or (configPath + "/rates.json")

        if not os.path.exists(workingHoursPath):
            sys.exit('Working hours file path does not exist: ' + workingHoursPath)
        if not os.path.exists(ratesPath):
            sys.exit('Rates file path does not exist: ' + ratesPath)
        
        self.workingHours = pandas.read_json(workingHoursPath)
        print("Loaded " + workingHoursPath)

        ratesData = json.load(open(ratesPath))
        self.rates = pandas.json_normalize(ratesData, record_path='Default')
        print("Loaded " + ratesPath)
        
        self.rates['User'] = [
                users.values.tolist()
                for _ in range(len(self.rates))]
        self.rates = self.rates.explode('User')
        exceptions = pandas.json_normalize(
            ratesData,
            record_path='Exceptions')
        self.rates = self.rates.merge(
            exceptions,
            on=['Key', 'User'],
            how="left")
        rcol = self.rates['Rate_y'].fillna(self.rates['Rate_x'])
        self.rates['Rate'] = rcol
        self.rates = self.rates.drop(columns=['Rate_x', 'Rate_y'])
        self.rates = self.rates.astype({'Rate': 'int'})
