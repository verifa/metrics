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


def leapYear(year: int) -> bool:
    """return True for leap years"""
    return ((year % 4 == 0) and (year % 100 != 0)) or (year % 400 == 0)


def lastMonthDay(month: str) -> str:
    """expects YYYY-MM as input returns YYYY-MM-XX where XX is the last day for month MM"""
    y, m = month.split("-")
    day = 30
    if m == "02":
        if leapYear(int(y)):
            day = 29
        else:
            day = 28
    if m in ["01", "03", "05", "07", "08", "10", "12"]:
        day = 31

    return f"{month}-{day}"


def splitMonthTable(df: pd.DataFrame) -> pd.DataFrame:
    """split the table into two entries per month"""
    first = df.copy()
    first["Month"] = [pd.Timestamp(f"{x}-01") for x in first["Month"]]
    last = df.copy()
    last["Month"] = [pd.Timestamp(lastMonthDay(x)) for x in last["Month"]]
    result = pd.concat([first, last], ignore_index=True, sort=True)
    result["Weekly"] = result["Cost"] * 12 / 52
    result["WeeklyExt"] = result["External_cost"] * 12 / 52
    if "Real_income" in result:
        result["WeeklyIn"] = result["Real_income"] * 12 / 52
    result["Year"] = result["Month"].dt.strftime("%Y")
    return result.sort_values(by=["Month"])
