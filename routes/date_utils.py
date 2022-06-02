import numpy
import pandas

def weekdays(from_date: str, to_date: str):
    """Returns the number of weekdays between the dates using numpy"""
    return 1 + numpy.busday_count(from_date, to_date, weekmask="1111100")

def lookAhead(offset: int, from_date :str = pandas.Timestamp('today')):
    return pandas.Timestamp(from_date).floor('D') + pandas.offsets.Day(offset)

def lookBack(offset: int, from_date :str = pandas.Timestamp('today')):
    return pandas.Timestamp(from_date).floor('D') - pandas.offsets.Day(offset)

