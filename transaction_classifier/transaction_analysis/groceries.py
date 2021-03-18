import pandas as pd
import numpy as np
from sqlalchemy import create_engine


qry = "SELECT * FROM banking_db.transactions where category='GROCERIES';"

engine = create_engine("mysql://root:@localhost/banking_db")
transactions_df = pd.read_sql(qry, engine, parse_dates=True)
transactions_df = transactions_df.fillna(value=np.nan)
transactions_df = transactions_df.sort_values(by='trans_date')

transactions_df = transactions_df.set_index('trans_date')

transactions_summary_df = pd.pivot_table(transactions_df, values='amount', columns=['category'], aggfunc=np.sum)

transactions_weekly_summary_df = pd.pivot_table(transactions_df, index=transactions_df.index, values='amount', columns=['category'], aggfunc=np.sum).resample('w').sum()
transactions_weekly_summary_df['mean'] = transactions_weekly_summary_df['GROCERIES'].rolling(15).mean()

transactions_weekly_summary_df.plot()
