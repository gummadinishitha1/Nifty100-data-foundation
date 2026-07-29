import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.db import get_companies, get_trend_metrics
from utils.formatting import display_na


st.title("Trend Analysis")

companies = get_companies()
search = st.text_input("Search company or ticker", placeholder="Type company name or ticker")
choices = companies.assign(label=companies["company_name"].fillna("") + " (" + companies["ticker"].fillna("") + ")")
if search:
    needle = search.strip().lower()
    choices = choices[
        choices["ticker"].str.lower().str.contains(needle, na=False)
        | choices["company_name"].str.lower().str.contains(needle, na=False)
    ]

if choices.empty:
    st.info("Ticker not found - please try another")
    st.stop()

label = st.selectbox("Company", choices["label"].tolist())
ticker = choices.loc[choices["label"].eq(label), "ticker"].iloc[0]
trends = get_trend_metrics(ticker)
if 0 < len(trends) < 10:
    st.caption(f"Data available for {len(trends)} years; charts use the available history.")

metric_options = {
    "Revenue": "revenue",
    "Net Profit": "net_profit",
    "ROE": "roe",
    "ROCE": "roce",
    "D/E": "debt_to_equity",
    "P/E": "pe_ratio",
    "P/B": "pb_ratio",
    "OPM": "opm",
    "NPM": "npm",
    "FCF": "fcf",
}
selected_metrics = st.multiselect("Metrics", list(metric_options), default=["Revenue", "Net Profit"], max_selections=3)

if not selected_metrics:
    st.info("Select up to 3 metrics to view the trend.")
    st.stop()

fig = go.Figure()
for metric in selected_metrics:
    column = metric_options[metric]
    values = pd.to_numeric(trends[column], errors="coerce")
    yoy = values.pct_change() * 100
    text = ["" if pd.isna(value) else f"{value:+.1f}%" for value in yoy]
    fig.add_scatter(
        x=trends["year"],
        y=values,
        mode="lines+markers+text",
        text=text,
        textposition="top center",
        name=metric,
    )

fig.update_layout(
    xaxis_title="Year",
    yaxis_title="Value",
    margin=dict(l=10, r=10, t=25, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig, width="stretch")
st.dataframe(display_na(trends), width="stretch", hide_index=True)
