import pandas as pd
import plotly.express as px
import streamlit as st

from utils.db import get_sectors, get_yearly_universe
from utils.formatting import display_na


st.title("Nifty 100 Analytics")
st.caption("Company fundamentals, screening, peer comparisons, sector views, and valuation snapshots.")

year = st.sidebar.selectbox("Year", list(range(2019, 2025)), index=5)
companies = get_yearly_universe(year)
sectors = get_sectors()


def numeric(column: str) -> pd.Series:
    return pd.to_numeric(companies[column], errors="coerce")


metric_cols = st.columns(6)
metric_cols[0].metric("Average ROE", f"{numeric('return_on_equity_pct').mean():.1f}%")
metric_cols[1].metric("Median P/E", f"{numeric('pe_ratio').median():.1f}")
metric_cols[2].metric("Median D/E", f"{numeric('debt_to_equity').median():.2f}")
metric_cols[3].metric("Total Companies", len(companies))
metric_cols[4].metric("Median Revenue CAGR 5yr", f"{numeric('revenue_cagr_5yr').median():.1f}%")
metric_cols[5].metric("Debt-Free Companies", int((numeric("debt_to_equity").fillna(0) <= 0.1).sum()))

left, right = st.columns([1, 1.25])
with left:
    st.subheader("Sector Breakdown")
    fig = px.pie(
        sectors,
        names="broad_sector",
        values="company_count",
        hole=0.55,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Top 5 Quality Score")
    top_quality = companies.nlargest(5, "composite_quality_score")[
        ["ticker", "company_name", "broad_sector", "composite_quality_score", "return_on_equity_pct", "revenue_cagr_5yr"]
    ].rename(
        columns={
            "ticker": "Ticker",
            "company_name": "Company",
            "broad_sector": "Sector",
            "composite_quality_score": "Composite Score",
            "return_on_equity_pct": "ROE %",
            "revenue_cagr_5yr": "Revenue CAGR 5yr %",
        }
    )
    st.dataframe(display_na(top_quality), width="stretch", hide_index=True)

st.subheader(f"Universe Snapshot - {year}")
st.dataframe(
    display_na(companies[
        [
            "ticker",
            "company_name",
            "broad_sector",
            "sub_sector",
            "return_on_equity_pct",
            "pe_ratio",
            "debt_to_equity",
            "revenue_cagr_5yr",
            "composite_quality_score",
        ]
    ]),
    width="stretch",
    hide_index=True,
)
