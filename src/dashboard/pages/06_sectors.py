import pandas as pd
import plotly.express as px
import streamlit as st

from utils.db import get_sector_company_metrics, get_sectors
from utils.formatting import display_na


st.title("Sector Analysis")

year = st.sidebar.selectbox("Year", list(range(2019, 2025)), index=5)
sectors = get_sectors()
sector = st.selectbox("Sector", sectors["broad_sector"].tolist())
data = get_sector_company_metrics(sector, year)

st.subheader(f"{sector} Companies")
bubble = data.dropna(subset=["revenue", "roe"]).copy()
if bubble.empty:
    st.info("No revenue and ROE data available for this sector/year.")
else:
    bubble["market_cap_crore"] = pd.to_numeric(bubble["market_cap_crore"], errors="coerce").fillna(1).clip(lower=1)
    fig = px.scatter(
        bubble,
        x="revenue",
        y="roe",
        size="market_cap_crore",
        color="sub_sector",
        hover_name="company_name",
        hover_data=["ticker", "market_cap_crore", "net_profit", "roce"],
        labels={"revenue": "Revenue (Rs Cr)", "roe": "ROE %", "market_cap_crore": "Market Cap (Rs Cr)"},
        size_max=55,
    )
    fig.update_layout(margin=dict(l=10, r=10, t=25, b=10))
    st.plotly_chart(fig, width="stretch")

kpi_columns = ["revenue", "roe", "roce", "debt_to_equity", "pe_ratio", "pb_ratio", "opm", "npm", "revenue_cagr_5yr"]
medians = (
    data[kpi_columns]
    .apply(pd.to_numeric, errors="coerce")
    .median()
    .reset_index()
    .rename(columns={"index": "metric", 0: "median"})
)
st.subheader("Sector Median KPIs")
bar = px.bar(medians, x="metric", y="median", color="metric", text_auto=".1f")
bar.update_layout(showlegend=False, margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(bar, width="stretch")
st.dataframe(display_na(data), width="stretch", hide_index=True)
