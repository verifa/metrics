""" Config module"""
import pandas as pd

from routes.date_utils import lookBack

START_DATE = pd.Timestamp("2021-01-01")
TODAY = pd.Timestamp("today")
YESTERDAY = TODAY - pd.to_timedelta("1day")
ROLLING_DATE = lookBack(180)
