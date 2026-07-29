import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.db import get_peer_groups, get_peers, get_screener_universe
from utils.formatting import display_na


st.title("Peer Comparison")

groups = get_peer_groups()
if groups.empty:
    st.info("No peer groups loaded.")
    st.stop()

group_name = st.selectbox("Peer group", groups["peer_group_name"].tolist())
peers = get_peers(group_name)
universe = get_screener_universe()
peers = peers.merge(
    universe[["ticker", "net_profit_margin_pct", "operating_profit_margin_pct", "revenue_cagr_5yr", "pat_cagr_5yr"]],
    on="ticker",
    how="left",
)

company_options = (peers["company_name"].fillna(peers["ticker"]) + " (" + peers["ticker"] + ")").tolist()
selected_label = st.selectbox("Benchmark company", company_options)
selected_ticker = peers.iloc[company_options.index(selected_label)]["ticker"]

metrics = {
    "Quality": "composite_quality_score",
    "ROE": "return_on_equity_pct",
    "ROCE": "return_on_capital_employed_pct",
    "D/E": "debt_to_equity",
    "OPM": "operating_profit_margin_pct",
    "NPM": "net_profit_margin_pct",
    "Revenue CAGR": "revenue_cagr_5yr",
    "FCF": "free_cash_flow_cr",
}

radar = peers[["ticker", *metrics.values()]].copy()
for column in metrics.values():
    radar[column] = pd.to_numeric(radar[column], errors="coerce")
    min_value = radar[column].min()
    max_value = radar[column].max()
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        radar[column] = 50
    else:
        radar[column] = (radar[column] - min_value) / (max_value - min_value) * 100

selected = radar.loc[radar["ticker"].eq(selected_ticker)].iloc[0]
average = radar[list(metrics.values())].mean()
labels = list(metrics.keys())
selected_values = [selected[column] for column in metrics.values()]
average_values = [average[column] for column in metrics.values()]

fig = go.Figure()
fig.add_trace(go.Scatterpolar(r=selected_values, theta=labels, fill="toself", name=selected_ticker))
fig.add_trace(go.Scatterpolar(r=average_values, theta=labels, fill="toself", name="Peer average"))
fig.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    margin=dict(l=20, r=20, t=30, b=20),
)
st.plotly_chart(fig, width="stretch")

table = peers[
    [
        "ticker",
        "company_name",
        "is_benchmark",
        "composite_quality_score",
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "debt_to_equity",
        "pe_ratio",
        "pb_ratio",
        "free_cash_flow_cr",
        "revenue_cagr_5yr",
    ]
].rename(columns={"ticker": "company_id", "company_name": "name"})


def highlight_benchmark(row: pd.Series) -> list[str]:
    return ["background-color: #e7f5e7; font-weight: 600" if row["is_benchmark"] else "" for _ in row]


st.subheader("Peer Group KPIs")
st.dataframe(display_na(table).style.apply(highlight_benchmark, axis=1), width="stretch", hide_index=True)
