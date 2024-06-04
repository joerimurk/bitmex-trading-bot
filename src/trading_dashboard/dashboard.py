from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from bitcoin_value import currency

df_balance = pd.read_sql("balance", "sqlite:///trades.db")
df_trades = pd.read_sql("orders", "sqlite:///trades.db")

bitcoin_balance = np.round(
    df_balance[df_balance["timestamp"] == df_balance["timestamp"].max()][
        "balance_after"
    ].iloc[0],
    6,
)
euro_balance = np.round(currency("EUR") * bitcoin_balance, 2)

btc_balance_min = (
    df_balance["balance_after"].min() - df_balance["balance_after"].min() * 0.005
)
btc_balance_max = (
    df_balance["balance_after"].max() + df_balance["balance_after"].max() * 0.005
)
timestamp_min = df_balance["timestamp"].min()
timestamp_max = datetime.now()

df_last_ten_trades = df_trades.sort_values("timestamp", ascending=False).iloc[:10][
    ["timestamp", "quantity", "price"]
]

st.header("Bitmex Trading Bot")

col1, col2 = st.columns(2)
col1.metric("Bitcoin balance", f"{bitcoin_balance}", "0%")
col2.metric("Euro balance", f"€ {euro_balance}")

st.plotly_chart(
    px.line(
        df_balance,
        x="timestamp",
        y="balance_after",
        range_x=[timestamp_min, timestamp_max],
        range_y=[btc_balance_min, btc_balance_max],
    ).update_layout(
        xaxis_title="Time",
        yaxis_title="Balance",
    ),
    config={"staticPlot": True},
)

st.table(df_last_ten_trades)
