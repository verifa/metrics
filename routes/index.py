"""System module."""
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as ff
from dash import dcc, html
from routes.tempo import TempoConfig, TempoData

startDate = "2021-01-01"

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
    dcc.Tab(label='Popular projects', value='fig3'),
    dcc.Tab(label='Projects', value='projects'),
    dcc.Tab(label='Egg Baskets', value='eggbaskets'),
    dcc.Tab(label='Rolling time', value='RollingTime'),
    dcc.Tab(label='Rolling income', value='rollingIncome'),
    dcc.Tab(label='Company weekly income', value='rollingAllIncomeTotal')
    ])

pageheader = html.Div([
    dcc.Markdown('## Verifa Metrics Dashboard'),
    dcc.Markdown(f'''
    #### For data between {work.from_date} and {work.to_date}
    # ''')
    ])


tabDict = {
    'table1': [table1],
    'table2': [table2],
    'billable': [billable],
    'internal': [internal],
    'fig3': [fig3],
    'projects': [time4, time3],
    'eggbaskets': [eggbaskets],
    'RollingTime': [rollingTeamAverage, rollingAll],
    'rollingIncome': [rollingTeamAverageIncome, rollingAllIncome],
    'rollingAllIncomeTotal': [rollingAllIncomeTotal]
    }


def render_content(tab):
    sections = [dcc.Graph(id="plot", figure=x) for x in tabDict[tab]]
    return html.Div(
        html.Section(children=sections)
    )
