import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.db import get_company_profile, get_company_pros_cons, get_companies, get_trend_metrics, get_yearly_universe
from utils.formatting import fmt_num, fmt_pct


st.title("Company Profile")

companies = get_companies()
search = st.text_input("Search company or ticker", placeholder="Type HDFCBANK, Reliance, TCS...")
choices = companies.assign(
    label=companies["company_name"].fillna("") + " (" + companies["ticker"].fillna("") + ")"
)
if search:
    needle = search.strip().lower()
    choices = choices[
        choices["ticker"].str.lower().str.contains(needle, na=False)
        | choices["company_name"].str.lower().str.contains(needle, na=False)
    ]

if choices.empty:
    st.info("Ticker not found - please try another")
    st.stop()

label = st.selectbox("Matching companies", choices["label"].tolist())
ticker = choices.loc[choices["label"].eq(label), "ticker"].iloc[0]
profile_df = get_company_profile(ticker)

if profile_df.empty:
    st.info("Ticker not found - please try another")
    st.stop()

profile = profile_df.iloc[0]
latest = get_yearly_universe(2024)
latest_row = latest.loc[latest["ticker"].eq(ticker)]
latest_row = latest_row.iloc[0] if not latest_row.empty else pd.Series(dtype=object)
trends = get_trend_metrics(ticker)

st.subheader(profile["company_name"])
card_cols = st.columns([1, 1, 1, 1])
card_cols[0].metric("Sector", profile.get("broad_sector") or "Unassigned")
card_cols[1].metric("Sub-sector", profile.get("sub_sector") or "Unassigned")
card_cols[2].metric("NSE Ticker", ticker)
card_cols[3].metric("Market Cap Category", profile.get("market_cap_category") or "N/A")
st.write(profile.get("about_company") or "No company description available.")


kpi_cols = st.columns(6)
kpi_cols[0].metric("ROE", fmt_pct(latest_row.get("return_on_equity_pct")))
kpi_cols[1].metric("ROCE", fmt_pct(latest_row.get("return_on_capital_employed_pct")))
kpi_cols[2].metric("Net Profit Margin", fmt_pct(latest_row.get("net_profit_margin_pct")))
kpi_cols[3].metric("D/E", fmt_num(latest_row.get("debt_to_equity")))
kpi_cols[4].metric("Revenue CAGR 5yr", fmt_pct(latest_row.get("revenue_cagr_5yr")))
kpi_cols[5].metric("FCF", fmt_num(latest_row.get("free_cash_flow_cr"), " Cr"))

left, right = st.columns(2)
with left:
    st.subheader("Revenue and Net Profit")
    if 0 < len(trends) < 10:
        st.caption(f"Data available for {len(trends)} years; charts use the available history.")
    bar_fig = go.Figure()
    bar_fig.add_bar(x=trends["year"], y=trends["revenue"], name="Revenue")
    bar_fig.add_bar(x=trends["year"], y=trends["net_profit"], name="Net Profit")
    bar_fig.update_layout(barmode="group", yaxis_title="Rs Cr", margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(bar_fig, width="stretch")

with right:
    st.subheader("ROE and ROCE")
    if 0 < len(trends) < 10:
        st.caption(f"Data available for {len(trends)} years; charts use the available history.")
    line_fig = go.Figure()
    line_fig.add_scatter(x=trends["year"], y=trends["roe"], name="ROE", mode="lines+markers", yaxis="y")
    line_fig.add_scatter(x=trends["year"], y=trends["roce"], name="ROCE", mode="lines+markers", yaxis="y2")
    line_fig.update_layout(
        yaxis=dict(title="ROE %"),
        yaxis2=dict(title="ROCE %", overlaying="y", side="right"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(line_fig, width="stretch")

pros_cons = get_company_pros_cons(ticker)
pros = pros_cons["pros"].dropna().tolist()
cons = pros_cons["cons"].dropna().tolist()
pros_col, cons_col = st.columns(2)
with pros_col:
    st.subheader("Pros")
    for item in pros or ["No pros loaded."]:
        st.success(item, icon="✅")
with cons_col:
    st.subheader("Cons")
    for item in cons or ["No cons loaded."]:
        st.error(item, icon="❌")
