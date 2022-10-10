"""Various date utility functions"""
import numpy as np
import pandas as pd


def weekdays(from_date: str, to_date: str):
    """Returns the number of weekdays between the dates using np"""
    return np.busday_count(from_date, str(lookAhead(1, to_date).date()), weekmask="1111100")


def lookAhead(offset: int, from_date: str = pd.Timestamp("today")):
    return pd.Timestamp(from_date).floor("D") + pd.offsets.Day(offset)


def lookBack(offset: int, from_date: str = pd.Timestamp("today")):
    return pd.Timestamp(from_date).floor("D") - pd.offsets.Day(offset)
