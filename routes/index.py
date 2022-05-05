"""System module."""
import json
import os
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import dcc, html
from tempoapiclient import client

# really wanted this in tempo/tempodata.py but
# could not convince poetry to accept it
tempokey = os.environ.get("TEMPO_KEY")

tempo = client.Tempo(
    auth_token=tempokey,
    base_url="https://api.tempo.io/core/3")


class TempoConfig:
    """TempoConfig data class"""
    # where to find the config files
    configPath = os.environ.get("TEMPO_CONFIG_PATH")
    if configPath is None:
        # default path
        configPath = '/tempo'
    # which config files are possible
    workingHoursFile = configPath + "/workinghours.json"
    ratesFile = configPath + "/rates.json"

    def __init__(self, users):
        self.workingHours = pd.DataFrame()
        if os.path.exists(self.workingHoursFile):
            self.workingHours = pd.read_json(self.workingHoursFile)
            print("Loaded " + self.workingHoursFile)
        self.rates = pd.DataFrame()
        if os.path.exists(self.ratesFile):
            ratesData = json.load(open(self.ratesFile))
            print("Loaded " + self.ratesFile)
            self.rates = pd.json_normalize(ratesData, record_path='Default')
            self.rates['User'] = [
                users.values.tolist()
                for _ in range(len(self.rates))]
            self.rates = self.rates.explode('User')
            exceptions = pd.json_normalize(
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
            print(self.rates)


class TempoData:
    """Tempo data class."""

    def __init__(self, fromDate, toDate):
        self.from_date = fromDate
        self.to_date = toDate
        self.logs = tempo.get_worklogs(
            dateFrom=self.from_date,
            dateTo=self.to_date
        )
        self.raw = pd.json_normalize(self.logs)
        self.data = self.raw[[
            "issue.key",
            "timeSpentSeconds",
            "billableSeconds",
            "startDate",
            "author.displayName"]]
        self.data.columns = [
            "Key",
            "Time",
            "Billable",
            "Date",
            "User"]
        df = pd.DataFrame(
            self.data.loc[:, ('Key')].str.split('-', 1).tolist(),
            columns=['Group', 'Number'])
        self.data.loc[:, ('Group')] = df['Group']
        self.data.loc[:, ('Date')] = pd.to_datetime(
            self.data.loc[:, ('Date')], format='%Y-%m-%d')
        self.data.loc[:, ('Time')] = self.data.loc[:, ('Time')]/3600
        self.data.loc[:, ('Billable')] = self.data.loc[:, ('Billable')]/3600
        self.data.loc[:, ('Internal')] = (
            self.data.loc[:, ('Time')] -
            self.data.loc[:, ('Billable')])

    def getUsers(self):
        """returns list of users
        """
        return self.data['User'].drop_duplicates()

    def byGroup(self):
        """returns aggregated time and billable time
        grouped by date, user and group
        """
        return(
            self.data.groupby(
                ['Date', 'User', 'Group'], as_index=False)
            [['Time', 'Billable']].sum())

    def byTotalGroup(self, daysBack):
        """returns aggregated billable time
        grouped by issue key group and user
        """
        lookBack = pd.Timestamp('today').floor('D') - pd.offsets.Day(daysBack)
        timedData = self.data[self.data['Date'] > lookBack]
        df = (timedData.groupby(
            ['Group', 'User'], as_index=False)
            [['Billable']].sum())
        df['Billable'].replace(0, np.nan, inplace=True)
        df.dropna(subset=['Billable'], inplace=True)
        return df

    def byEggBaskets(self, rates):
        """returns aggregated billable income
        grouped by issue key group, user and time box (30, 60, 90)
        """
        lookBack30 = pd.Timestamp('today').floor('D') - pd.offsets.Day(30)
        lookBack60 = pd.Timestamp('today').floor('D') - pd.offsets.Day(60)
        lookBack90 = pd.Timestamp('today').floor('D') - pd.offsets.Day(90)

        baskets = self.data
        baskets['TimeBasket'] = '0'
        baskets.loc[
            baskets['Date'] > lookBack90,
            'TimeBasket'] = '60-90 days ago'
        baskets.loc[
            baskets['Date'] > lookBack60,
            'TimeBasket'] = '30-60 days ago'
        baskets.loc[
            baskets['Date'] > lookBack30,
            'TimeBasket'] = '0-30 days ago'
        baskets['TimeBasket'].replace('0', np.nan, inplace=True)
        baskets.dropna(subset=['TimeBasket'], inplace=True)

        upRated = baskets.merge(rates, on=['Key', 'User'], how="left")
        upRated['Rate'] = upRated.apply(
            lambda x: x['Rate']/10 if x['Currency'] == 'SEK' else x['Rate'],
            axis=1)
        upRated['Income'] = upRated['Rate'] * upRated['Billable']
        df = (upRated.groupby(
            ['Group', 'User', 'TimeBasket'], as_index=False)
            [['Income']].sum())
        df['Income'].replace(0, np.nan, inplace=True)
        df.dropna(subset=['Income'], inplace=True)
        return df

    def byDay(self):
        """returns aggregated time and billable time
        grouped by date, user and issue key
        """
        return(
            self.data.groupby(
                ['Date', 'User', 'Key'], as_index=False)
            [['Time', 'Billable']].sum())

    def byUser(self, workingHours=None):
        """returns aggregated time and billable time
        grouped by user
        """
        userData = (
            self.data.groupby('User', as_index=False)
            [['Time', 'Billable']].sum()
        )
        if not workingHours.empty:
            print(workingHours)
            tmpData = pd.merge(userData, workingHours, on="User")
            userData = tmpData

        return(
            userData
        )

    def userRolling7(self):
        """returns rolling 7 day sums for Billable and non Billable time
        grouped by user
        """
        dailySum = (
            self.data.groupby(
                ['Date', 'User'], as_index=False)
            [['Billable', 'Internal']].sum()
        )
        rolling7Sum = (
            dailySum.set_index('Date').groupby(
                ['User'], as_index=False).rolling('7d')
            [['Billable', 'Internal']].sum()
        )
        return(
            rolling7Sum.reset_index(inplace=False)
        )

#
# =========================================================
#


def teamRollingAverage7(r7):
    dailyAverage = (
        r7.groupby(
            ['Date'])
        [['Billable', 'Internal']].mean()
    )
    return dailyAverage.reset_index(inplace=False)


def rollingAverage30(dailyData):
    monthlyAvg = (
        dailyData.set_index('Date').rolling('30d')
        [['Billable', 'Internal']].mean()
    )
    return monthlyAvg.reset_index(inplace=False)


#
# =========================================================
#


# Fetch the data from tempo
work = TempoData("2022-01-01", str(date.today()))

# read config files
tc = TempoConfig(work.getUsers())

rolling7 = work.userRolling7()

table1 = ff.create_table(work.byUser(tc.workingHours))

rollingAll = px.scatter(
    rolling7,
    x='Date',
    y=['Billable', 'Internal'],
    facet_col='User',
    facet_col_wrap=3,
    height=800
)
rollingAll.update_layout(title="Rolling 7 days")

teamRollingAverage7 = teamRollingAverage7(rolling7)
teamRollingAverage30 = rollingAverage30(teamRollingAverage7)
teamRollingAverage30.columns = ["Date", "Billable30", "Internal30"]
teamRollingAverage30 = teamRollingAverage30.merge(
    teamRollingAverage7,
    on=['Date'])
rollingTeamAverage = px.scatter(
    teamRollingAverage30,
    x='Date',
    y=['Billable', 'Billable30', 'Internal', 'Internal30'],
    color_discrete_sequence=[
        '#8FBC8F',
        '#006400',
        '#FF7F50',
        '#A52A2A'],
    height=600
)
rollingTeamAverage.update_layout(title="Team average, rolling 7 days")

time1 = px.histogram(
    work.byDay().sort_values("Key"),
    x='Date',
    y='Time',
    color='Key',
    facet_col='User',
    facet_col_wrap=3,
    height=800
)
time1.update_layout(
    bargap=0.1,
    title="What do we work on")

time2 = px.histogram(
    work.byDay().sort_values("Key"),
    x='Date',
    y='Time',
    color='Key',
    height=600
)
time2.update_layout(
    bargap=0.1,
    title="What do we work on")

time3 = px.histogram(
    work.byGroup().sort_values("Group"),
    x='Date',
    y='Time',
    color='Group',
    facet_col='User',
    facet_col_wrap=3,
    height=800
)
time3.update_layout(
    bargap=0.1,
    title="What do we work on")

time4 = px.histogram(
    work.byGroup().sort_values("Group"),
    x='Date',
    y='Time',
    color='Group',
    height=600
)
time4.update_layout(
    bargap=0.1,
    title="What do we work on")

daysAgo = 90
if tc.rates.empty:
    yAxisTitle = "Sum of billable time"
    eggbaskets = px.histogram(
        work.byTotalGroup(daysAgo),
        x='Group',
        y='Billable',
        color='User'
    )
    eggbaskets.update_xaxes(categoryorder='total ascending')
else:
    yAxisTitle = "Sum of Income (Euro)"
    eggbaskets = px.histogram(
        work.byEggBaskets(tc.rates),
        x='Group',
        y='Income',
        color='User',
        facet_col='TimeBasket',
        facet_col_wrap=3,
        category_orders={
            "TimeBasket": [
                "60-90 days ago",
                "30-60 days ago",
                "0-30 days ago"]}
    )
eggbaskets.update_layout(
    height=600,
    yaxis_title=yAxisTitle,
    bargap=0.1,
    title="Baskets for our eggs (" + str(daysAgo) + " days back)")

billable = px.histogram(
    work.data.sort_values("Key"),
    x="User",
    y="Billable",
    color="Key",
    height=600)

billable.update_xaxes(categoryorder='total ascending')

internal = px.histogram(
    work.data.sort_values("Key"),
    x="User",
    y="Internal",
    color="Key",
    height=600)

internal.update_xaxes(categoryorder='total descending')

fig2 = px.histogram(
    work.data,
    x="Key",
    y="Time",
    color="User",
    height=600)

fig2.update_xaxes(categoryorder='total ascending')

#
# =========================================================
#

tabStructure = dcc.Tabs(id="tabs-graph", value='table1', children=[
    dcc.Tab(label='Aggregated', value='table1'),
    dcc.Tab(label='Billable', value='billable'),
    dcc.Tab(label='Internal', value='internal'),
    dcc.Tab(label='Popular keys', value='fig2'),
    dcc.Tab(label='Keys Personal', value='time1'),
    dcc.Tab(label='Keys Team', value='time2'),
    dcc.Tab(label='Projects Personal', value='time3'),
    dcc.Tab(label='Projects Team', value='time4'),
    dcc.Tab(label='EggBaskets', value='eggbaskets'),
    dcc.Tab(label='Rolling individual', value='rollingAll'),
    dcc.Tab(label='Rolling team', value='rollingTeamAverage')
    ])

pageheader = html.Div([
    dcc.Markdown('## Verifa Metrics Dashboard'),
    dcc.Markdown(f'''
    #### For data between {work.from_date} and {work.to_date}
    # ''')
    ])


tabDict = {
    'table1': table1,
    'billable': billable,
    'internal': internal,
    'fig2': fig2,
    'time1': time1,
    'time2': time2,
    'time3': time3,
    'time4': time4,
    'eggbaskets': eggbaskets,
    'rollingAll': rollingAll,
    'rollingTeamAverage': rollingTeamAverage
    }


def render_content(tab):
    return html.Div(
        html.Section(children=[
            dcc.Graph(id="plot", figure=tabDict[tab])
        ])
    )
