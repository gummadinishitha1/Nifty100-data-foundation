import pandas as pd
import plotly.express as px
import streamlit as st

from utils.db import get_capital_allocation_map


st.title("Capital Allocation Map")

data = get_capital_allocation_map()
summary = (
    data.groupby("allocation_pattern", as_index=False)
    .agg(company_count=("ticker", "count"), market_cap_crore=("market_cap_crore", "sum"))
    .sort_values("company_count", ascending=False)
)

fig = px.treemap(
    data,
    path=["allocation_pattern", "company_name"],
    values="market_cap_crore",
    color="allocation_pattern",
    hover_data=["ticker", "broad_sector", "return_on_equity_pct", "debt_to_equity", "free_cash_flow_cr"],
)
fig.update_layout(margin=dict(l=10, r=10, t=20, b=10))

event = st.plotly_chart(fig, width="stretch", on_select="rerun", selection_mode="points")
patterns = summary["allocation_pattern"].tolist()
selected_pattern = None

try:
    points = event.selection.points
    if points:
        selected_pattern = points[0].get("label")
        if selected_pattern not in patterns:
            selected_pattern = points[0].get("parent")
except AttributeError:
    selected_pattern = None

fallback_index = patterns.index(selected_pattern) if selected_pattern in patterns else 0
selected_pattern = st.selectbox("Allocation pattern", patterns, index=fallback_index)

st.subheader(f"{selected_pattern} Companies")
filtered = data.loc[data["allocation_pattern"].eq(selected_pattern)].copy()
st.caption(f"{len(filtered)} companies in this pattern")
st.dataframe(
    filtered[
        [
            "ticker",
            "company_name",
            "broad_sector",
            "sub_sector",
            "return_on_equity_pct",
            "debt_to_equity",
            "free_cash_flow_cr",
            "revenue_cagr_5yr",
            "pat_cagr_5yr",
            "market_cap_crore",
        ]
    ],
    width="stretch",
    hide_index=True,
)

st.subheader("Pattern Summary")
st.dataframe(summary, width="stretch", hide_index=True)
