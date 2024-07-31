""" Config module"""

import pandas as pd

from metrics.date_utils import lookBack, monthBegin

START_DATE = pd.Timestamp("2021-01-01")
TODAY = pd.Timestamp("today")
YESTERDAY = TODAY - pd.to_timedelta("1day")
ROLLING_DATE = lookBack(360)
ALLOCATION_START = monthBegin(lookBack(90))
EUR2SEK = 11.60
EUR2DKK = 7.46
