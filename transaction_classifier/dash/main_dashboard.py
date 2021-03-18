import plotly.graph_objs as go
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
from dash.dependencies import Input, Output, State

import pandas as pd
import numpy as np
from sqlalchemy import create_engine

app = dash.Dash()

qry = "SELECT * FROM banking_db.transactions;"
pw = ''
engine = create_engine(f"mysql://root:{pw}@localhost/banking_db")
transactions_df = pd.read_sql(qry, engine, parse_dates=True)
transactions_df = transactions_df.fillna(value=np.nan)
transactions_df = transactions_df.sort_values(by='trans_date')

transactions_df = transactions_df.set_index('trans_date')

reduced_cols = ['date', 'vendor', 'amount', 'category']
transactions_reduced_df = transactions_df[reduced_cols]
options = [{'label': c, 'value': c} for c in transactions_reduced_df.category.unique()]
categories = transactions_reduced_df.category.unique()

transactions_summary_df = pd.pivot_table(transactions_df, values='amount', columns=['category'], aggfunc=np.sum)

transactions_monthly_summary_df = pd.pivot_table(transactions_df, index=transactions_df.index, values='amount', columns=['category'], aggfunc=np.sum).resample('MS').sum()

sum_df = pd.DataFrame()
sum_df['income'] = transactions_monthly_summary_df.where(transactions_monthly_summary_df > 0).sum(axis=1)
sum_df['expenses'] = transactions_monthly_summary_df.where(transactions_monthly_summary_df < 0).sum(axis=1)*-1
sum_df['savings'] = sum_df['income'] - sum_df['expenses']
sum_df['cum_savings'] = sum_df['savings'].cumsum()

transactions_sum_df = transactions_monthly_summary_df.mean(axis=0).to_frame()
transactions_sum_df.columns = ['expenses']
transactions_sum_df = transactions_sum_df.reset_index()
columns=[{'name': 'category', 'id': 'category'},
         {'name': 'expenses', 'id': 'expenses'}]


# date slider markers:
# https://community.plotly.com/t/solved-has-anyone-made-a-date-range-slider/6531/8
maxmarks=20*4
tday=pd.Timestamp.today() #gets timestamp of today
m1date=tday+pd.DateOffset(months=-maxmarks+1) #first month on slider
datelist=pd.date_range(m1date, periods=maxmarks, freq='M') # list of months as dates
dlist=pd.DatetimeIndex(datelist).normalize()
tags={} #dictionary relating marks on slider to tags. tags are shown as "Apr', "May', etc
datevalues={} #dictionary relating mark to date value
x=1
for i in dlist:
    # tags[x]=(i+pd.DateOffset(months=1)).strftime('%b-%y') #gets the string representation of next month ex:'Apr'
    tags[x] = (i + pd.DateOffset(months=1)).strftime('%b-%y')
    datevalues[x]=i
    x=x+1

fig = px.line(transactions_monthly_summary_df, x=transactions_monthly_summary_df.index,
              y=transactions_monthly_summary_df.columns, title='Ettie and Paul Monthly Expenses')

fig.update_layout(
    autosize=False,
    width=1850,
    height=800,
)

fig_sum = px.line(sum_df, x=sum_df.index,
              y=sum_df.columns, title='Income vs Expenses Total')

fig_sum.update_layout(
    autosize=False,
    width=1850,
    height=500,
)
# Now here's the Dash part:

app.layout = html.Div([
    html.Div(id='intermediate-value', style={'display': 'none'}),
    dcc.Graph(id='graph-sum', figure=fig_sum),
    html.P([html.Br()]),
    dcc.RangeSlider(
        id='month-slider',
        updatemode='mouseup',
        count=1,
        min=1,
        max=maxmarks,
        step=1,
        value=[1,maxmarks],
        marks=tags,
        pushable=1
    ),
    html.P([html.Br()]),
    dcc.Graph(id='graph', figure=fig),
    html.P([html.Br()]),
    html.Div([
        dash_table.DataTable(
            id='table',
            columns=[{'id': c, 'name': c} for c in transactions_sum_df.columns],
            data=transactions_sum_df.to_dict('records'),
            export_format='xlsx',
            export_headers='display'),
        html.P([html.Br()]),
        dcc.Dropdown(
            id='category-dropdown',
            options=options,
            value=categories,
            multi=True
        ),
        dash_table.DataTable(
            id='table-all-transactions',
            columns=[{'id': c, 'name': c} for c in transactions_reduced_df.columns],
            data=transactions_reduced_df.to_dict('records'),
            page_size=25,
            export_format='xlsx',
            export_headers='display')
    ])
])


@app.callback(
    Output('graph-sum', 'figure'),
    [Input('month-slider', 'value')])
def update_figure(range):

    filtered_df = transactions_monthly_summary_df[range[0]:range[1]]

    sum_df = pd.DataFrame()
    sum_df['income'] = filtered_df.where(filtered_df > 0).sum(axis=1)
    sum_df['expenses'] = filtered_df.where(filtered_df < 0).sum(axis=1) * -1
    sum_df['savings'] = sum_df['income'] - sum_df['expenses']
    sum_df['cum_savings'] = sum_df['savings'].cumsum()

    fig = px.line(sum_df, x=sum_df.index,
                  y=sum_df.columns, title='Income vs Expenses Total')

    fig.update_layout(
        autosize=False,
        width=1850,
        height=500,
    )
    fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output('graph', 'figure'),
    [Input('month-slider', 'value')])
def update_figure(range):

    filtered_df = transactions_monthly_summary_df[range[0]:range[1]]

    fig = px.line(filtered_df, x=filtered_df.index,
                  y=filtered_df.columns, title='Ettie and Paul Monthly Expenses')

    fig.update_layout(
        autosize=False,
        width=1850,
        height=800,
    )
    fig.update_layout(transition_duration=500)
    return fig


@app.callback(
    Output('table', 'data'),
    [Input('month-slider', 'value')])
def update_table(range):
    filtered_df = transactions_monthly_summary_df[range[0]:range[1]]
    transactions_sum_df = filtered_df.mean(axis=0).to_frame()
    transactions_sum_df.columns = ['expenses']
    transactions_sum_df = transactions_sum_df.reset_index()
    data = transactions_sum_df.to_dict('records')
    return data


@app.callback(
    Output('table-all-transactions', 'data'),
    [Input('month-slider', 'value'),
     Input('category-dropdown', 'value')],
    [State('month-slider', 'value'),
     State('category-dropdown', 'value')]
)
def update_transactions_table(date_range, dropdown_values, a, b):
    lower = date_range[0]
    upper = date_range[1]

    if upper >= len(dlist):
        upper = len(dlist)-1

    date_filtered_df = transactions_reduced_df.loc[dlist[lower]:dlist[upper]]
    category_and_date_filtered_df = date_filtered_df[date_filtered_df['category'].isin(dropdown_values)]
    data = category_and_date_filtered_df.to_dict('records')
    return data

@app.callback(Output('intermediate-value', 'children'), [Input('graph', 'selectedData')])
def test_callback(selected_data):
    a=1
    print(selected_data)



if __name__ == '__main__':
    app.run_server(debug=True)