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

startDate = "2021-01-01"


def weekdays(from_date, to_date):
    """ Returns the number of weekdays between the dates
        using numpy
    """
    begin = from_date
    end = to_date
    return 1 + np.busday_count(begin, end, weekmask='1111100')


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
            # print(self.rates)


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

    def uprateWork(self, rates):
        upRated = self.data.merge(rates, on=['Key', 'User'], how="left")
        upRated['Rate'] = upRated.apply(
            lambda x: x['Rate']/10 if x['Currency'] == 'SEK' else x['Rate'],
            axis=1)
        upRated['Income'] = upRated['Rate'] * upRated['Billable']
        work.data = upRated

    def byEggBaskets(self):
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
        df = (baskets.groupby(
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
        # Find the first time entry for each user
        userFirst = (
            self.data.groupby('User', as_index=False)
            ['Date'].min()
        )
        # Add a unique comumn name
        userFirst.columns = ['User', 'First']
        # Convert fime stamp to just date
        userFirst['First'] = [x.date() for x in userFirst['First']]
        # add the column to the user data
        userData = pd.merge(
            userData,
            userFirst,
            on='User'
        )
        userLast = (
            self.data.groupby('User', as_index=False)
            ['Date'].max()
        )
        userLast.columns = ['User', 'Last']
        userLast['Last'] = [x.date() for x in userLast['Last']]
        userData = pd.merge(
            userData,
            userLast,
            on='User'
        )
        userData['Days'] = [
            weekdays(f, t) for f, t in zip(
                userData['First'],
                userData['Last'])]
        if not workingHours.empty:
            # print(workingHours)
            tmpData = pd.merge(userData, workingHours, on="User")
            userData = tmpData
            userData['Expected'] = [d * d2 for d, d2 in zip(
                userData['Daily'], userData['Days'])]
            userData['Delta'] = [t - e for t, e in zip(
                userData['Time'], userData['Expected'])]

        return(
            userData
        )

    def ratesTable(self):
        rateData = self.data[self.data["Billable"] > 0]
        rateData = rateData.groupby('Key', as_index=False).agg(
            Hours=('Billable', np.sum),
            Rate=('Rate', np.mean))
        return(
            rateData.sort_values(
                by=["Rate", "Hours"],
                ascending=[True, False],
                na_position="first")
        )

    def userRolling7(self, tosum):
        """returns rolling 7 day sums for Billable and non Billable time
        grouped by user
        """
        dailySum = (
            self.data.groupby(
                ['Date', 'User'], as_index=False)
            [tosum].sum()
        )
        rolling7Sum = (
            dailySum.set_index('Date').groupby(
                ['User'], as_index=False).rolling('7d')
            [tosum].sum()
        )
        return(
            rolling7Sum.reset_index(inplace=False)
        )

    def teamRolling7(self, tosum):
        """returns rolling 7 day sums for Billable and non Billable time
        grouped by user
        """
        dailySum = (
            self.data.groupby(
                ['Date'], as_index=False)
            [tosum].sum()
        )
        rolling7Sum = (
            dailySum.set_index('Date').rolling('7d')
            [tosum].sum()
        )
        return(
            rolling7Sum.reset_index(inplace=False)
        )


#
# =========================================================
#


def teamRollingAverage7(r7, tomean):
    dailyAverage = (
        r7.groupby(
            ['Date'])
        [tomean].mean()
    )
    return dailyAverage.reset_index(inplace=False)


def rollingAverage(dailyData, tomean, days):
    monthlyAvg = (
        dailyData.set_index('Date').rolling(str(days)+'d')
        [tomean].mean()
    )
    return monthlyAvg.reset_index(inplace=False)


firstDays7 = pd.Timestamp(startDate).floor('D') + pd.offsets.Day(7)
firstDays30 = pd.Timestamp(startDate).floor('D') + pd.offsets.Day(30)
firstDays90 = pd.Timestamp(startDate).floor('D') + pd.offsets.Day(90)
firstDays365 = pd.Timestamp(startDate).floor('D') + pd.offsets.Day(365)

plotDaysAgo = pd.Timestamp('today').floor('D') - pd.offsets.Day(180)

#
# =========================================================
#


# Fetch the data from tempo
work = TempoData(startDate, str(date.today()))

# read config files
tc = TempoConfig(work.getUsers())

# add rate info to data
work.uprateWork(tc.rates)

# create aggregated table with all users
table1 = ff.create_table(work.byUser(tc.workingHours))

# create table with all rates
table2 = ff.create_table(work.ratesTable())

# Rolling individual (time)
rolling7 = work.userRolling7(['Billable', 'Internal'])
rolling7.loc[
    rolling7['Date'] < firstDays7, 'Billable'] = np.nan
rolling7.loc[
    rolling7['Date'] < firstDays7, 'Internal'] = np.nan
rollingAll = px.scatter(
    rolling7[rolling7["Date"] > plotDaysAgo],
    x='Date',
    y=['Billable', 'Internal'],
    facet_col='User',
    facet_col_wrap=3,
    height=800
)
rollingAll.update_layout(title="Rolling 7 days")

# Rolling team (time)
rollingAverage7 = teamRollingAverage7(rolling7, ['Billable', 'Internal'])
teamRollingAverage30 = rollingAverage(
    rollingAverage7, ['Billable', 'Internal'], 30)
teamRollingAverage30.columns = ["Date", "Billable30", "Internal30"]
teamRollingAverage30.loc[
    teamRollingAverage30['Date'] < firstDays30, 'Billable30'] = np.nan
teamRollingAverage30.loc[
    teamRollingAverage30['Date'] < firstDays30, 'Internal30'] = np.nan
teamRollingAverage30 = teamRollingAverage30.merge(
    rollingAverage7, on=['Date'])
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
rollingTeamAverage.update_layout(
    title="Team average, rolling 7 days, based on time",
    xaxis_rangeslider_visible=True,
    xaxis_range=[plotDaysAgo, str(date.today())]
)

# Rolling individual (income)
rollingIncome7 = work.userRolling7('Income')
rolling7.loc[
    rolling7['Date'] < firstDays7, 'Income'] = np.nan
rollingAllIncome = px.scatter(
    rollingIncome7[rollingIncome7["Date"] > plotDaysAgo],
    x='Date',
    y='Income',
    facet_col='User',
    facet_col_wrap=3,
    height=800
)
rollingAllIncome.update_layout(title="Rolling 7 days (income)")

# Rolling team (income)
rollingAverage7 = teamRollingAverage7(rollingIncome7, 'Income')
teamRollingAverage30 = rollingAverage(rollingAverage7, 'Income', 30)
teamRollingAverage30.columns = ["Date", "Income30"]
teamRollingAverage30.loc[
    teamRollingAverage30['Date'] < firstDays30, 'Income30'] = np.nan
teamRollingAverage30 = teamRollingAverage30.merge(
    rollingAverage7, on=['Date'])
rollingTeamAverageIncome = px.scatter(
    teamRollingAverage30,
    x='Date',
    y=['Income', 'Income30'],
    color_discrete_sequence=[
        '#8FBC8F',
        '#006400'],
    height=600
)
rollingTeamAverageIncome.update_layout(
    yaxis_title="Income (euro)",
    title="Team average, rolling 7 days, based on income",
    xaxis_rangeslider_visible=True,
    xaxis_range=[plotDaysAgo, str(date.today())]
)

# Weekly income
rollingIncome7 = work.teamRolling7('Income')
teamRollingAverage30 = rollingAverage(rollingIncome7, 'Income', 30)
teamRollingAverage30.columns = ["Date", "Income30"]
teamRollingAverage30 = teamRollingAverage30.merge(
    rollingIncome7, on=['Date'])
teamRollingAverage90 = rollingAverage(rollingIncome7, 'Income', 90)
teamRollingAverage90.columns = ["Date", "Income90"]
teamRollingAverage90 = teamRollingAverage90.merge(
    teamRollingAverage30, on=['Date'])
teamRollingAverage365 = rollingAverage(rollingIncome7, 'Income', 365)
teamRollingAverage365.columns = ["Date", "Income365"]
teamRollingAverage365 = teamRollingAverage365.merge(
    teamRollingAverage90, on=['Date'])

teamRollingAverage = teamRollingAverage365
teamRollingAverage.loc[
    teamRollingAverage['Date'] < firstDays7, 'Income'] = np.nan
teamRollingAverage.loc[
    teamRollingAverage['Date'] < firstDays30, 'Income30'] = np.nan
teamRollingAverage.loc[
    teamRollingAverage['Date'] < firstDays90, 'Income90'] = np.nan
teamRollingAverage.loc[
    teamRollingAverage['Date'] < firstDays365, 'Income365'] = np.nan

rollingAllIncomeTotal = px.scatter(
    teamRollingAverage,
    x='Date',
    y=['Income', 'Income30', 'Income90', 'Income365'],
    color_discrete_sequence=[
        '#C8E6C9',
        '#81C784',
        '#388E3C',
        '#1B5E20'],
    height=600
)
rollingAllIncomeTotal.update_layout(
    yaxis_title="Income (euro)",
    title="Weekly income",
    xaxis_rangeslider_visible=True,
    xaxis_range=[plotDaysAgo, str(date.today())]
)

# Keys personal
time1data = work.byDay().sort_values("Key")
time1 = px.histogram(
    time1data[time1data["Date"] > plotDaysAgo],
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

# Keys team
time2data = work.byDay().sort_values("Key")
time2 = px.histogram(
    time2data[time2data["Date"] > plotDaysAgo],
    x='Date',
    y='Time',
    color='Key',
    height=600
)
time2.update_layout(
    bargap=0.1,
    title="What do we work on")

# Projects personal
time3data = work.byGroup().sort_values("Group")
time3 = px.histogram(
    time3data[time3data["Date"] > plotDaysAgo],
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

# Projects team
time4data = work.byGroup().sort_values("Group")
time4 = px.histogram(
    time4data[time4data["Date"] > plotDaysAgo],
    x='Date',
    y='Time',
    color='Group',
    height=600
)
time4.update_layout(
    bargap=0.1,
    title="What do we work on")

# Billable time
billable = px.histogram(
    work.data.sort_values("Key"),
    x="User",
    y="Billable",
    color="Key",
    height=600)

billable.update_xaxes(categoryorder='total ascending')

# Internal time
internal = px.histogram(
    work.data.sort_values("Key"),
    x="User",
    y="Internal",
    color="Key",
    height=600)

internal.update_xaxes(categoryorder='total descending')

# Popular keys
fig2 = px.histogram(
    work.data,
    x="Key",
    y="Time",
    color="User",
    height=600)

fig2.update_xaxes(categoryorder='total ascending')

# Popular projects
fig3 = px.histogram(
    work.data,
    x="Group",
    y="Time",
    color="User",
    height=600)

fig3.update_xaxes(categoryorder='total ascending')

# Eggs and baskets
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
        work.byEggBaskets(),
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

#
# =========================================================
#

tabStructure = dcc.Tabs(id="tabs-graph", value='table1', children=[
    dcc.Tab(label='Our hours', value='table1'),
    dcc.Tab(label='Rates', value='table2'),
    dcc.Tab(label='Billable', value='billable'),
    dcc.Tab(label='Internal', value='internal'),
    dcc.Tab(label='Popular keys', value='fig2'),
    dcc.Tab(label='Popular projects', value='fig3'),
    dcc.Tab(label='Keys Personal', value='time1'),
    dcc.Tab(label='Keys Team', value='time2'),
    dcc.Tab(label='Projects Personal', value='time3'),
    dcc.Tab(label='Projects Team', value='time4'),
    dcc.Tab(label='Egg Baskets', value='eggbaskets'),
    dcc.Tab(label='Rolling individual (time)', value='rollingAll'),
    dcc.Tab(label='Rolling team (time)', value='rollingTeamAverage'),
    dcc.Tab(label='Rolling individual (income)', value='rollingAllIncome'),
    dcc.Tab(label='Rolling team (income)', value='rollingTeamAverageIncome'),
    dcc.Tab(label='Company weekly income', value='rollingAllIncomeTotal')
    ])

pageheader = html.Div([
    dcc.Markdown('## Verifa Metrics Dashboard'),
    dcc.Markdown(f'''
    #### For data between {work.from_date} and {work.to_date}
    # ''')
    ])


tabDict = {
    'table1': table1,
    'table2': table2,
    'billable': billable,
    'internal': internal,
    'fig2': fig2,
    'fig3': fig3,
    'time1': time1,
    'time2': time2,
    'time3': time3,
    'time4': time4,
    'eggbaskets': eggbaskets,
    'rollingAll': rollingAll,
    'rollingTeamAverage': rollingTeamAverage,
    'rollingAllIncome': rollingAllIncome,
    'rollingTeamAverageIncome': rollingTeamAverageIncome,
    'rollingAllIncomeTotal': rollingAllIncomeTotal
    }


def render_content(tab):
    return html.Div(
        html.Section(children=[
            dcc.Graph(id="plot", figure=tabDict[tab])
        ])
    )
