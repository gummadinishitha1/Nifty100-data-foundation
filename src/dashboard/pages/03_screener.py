import pandas as pd
import streamlit as st

from utils.db import get_screener_universe
from utils.formatting import display_na


st.title("Screener")

universe = get_screener_universe()

PRESETS = {
    "Quality": {"roe_min": 18.0, "de_max": 1.0, "fcf_min": 0.0, "revenue_cagr_min": 8.0, "pat_cagr_min": 8.0, "opm_min": 15.0, "pe_max": 80.0, "pb_max": 20.0, "dividend_yield_min": 0.0, "icr_min": 3.0},
    "Value": {"roe_min": 10.0, "de_max": 1.5, "fcf_min": 0.0, "revenue_cagr_min": 0.0, "pat_cagr_min": 0.0, "opm_min": 5.0, "pe_max": 25.0, "pb_max": 3.0, "dividend_yield_min": 0.0, "icr_min": 1.5},
    "Growth": {"roe_min": 12.0, "de_max": 2.0, "fcf_min": -500.0, "revenue_cagr_min": 12.0, "pat_cagr_min": 12.0, "opm_min": 8.0, "pe_max": 120.0, "pb_max": 30.0, "dividend_yield_min": 0.0, "icr_min": 1.0},
    "Dividend": {"roe_min": 8.0, "de_max": 2.0, "fcf_min": 0.0, "revenue_cagr_min": 0.0, "pat_cagr_min": 0.0, "opm_min": 5.0, "pe_max": 80.0, "pb_max": 20.0, "dividend_yield_min": 2.0, "icr_min": 1.5},
    "Debt-Free": {"roe_min": 8.0, "de_max": 0.1, "fcf_min": 0.0, "revenue_cagr_min": 0.0, "pat_cagr_min": 0.0, "opm_min": 0.0, "pe_max": 120.0, "pb_max": 30.0, "dividend_yield_min": 0.0, "icr_min": 0.0},
    "Turnaround": {"roe_min": 0.0, "de_max": 3.0, "fcf_min": -1000.0, "revenue_cagr_min": 0.0, "pat_cagr_min": -10.0, "opm_min": 0.0, "pe_max": 150.0, "pb_max": 30.0, "dividend_yield_min": 0.0, "icr_min": 0.0},
}

DEFAULTS = {"roe_min": 0.0, "de_max": 5.0, "fcf_min": -5000.0, "revenue_cagr_min": -25.0, "pat_cagr_min": -50.0, "opm_min": -25.0, "pe_max": 200.0, "pb_max": 50.0, "dividend_yield_min": 0.0, "icr_min": 0.0}

for key, value in DEFAULTS.items():
    st.session_state.setdefault(key, value)

st.sidebar.subheader("Presets")
for name, preset in PRESETS.items():
    if st.sidebar.button(name, width="stretch"):
        for key, value in preset.items():
            st.session_state[key] = value

st.sidebar.subheader("Filters")
roe_min = st.sidebar.slider("ROE min", 0.0, 60.0, key="roe_min", step=0.5)
de_max = st.sidebar.slider("D/E max", 0.0, 5.0, key="de_max", step=0.1)
fcf_min = st.sidebar.slider("FCF min", -5000.0, 20000.0, key="fcf_min", step=100.0)
revenue_cagr_min = st.sidebar.slider("Revenue CAGR min", -25.0, 50.0, key="revenue_cagr_min", step=0.5)
pat_cagr_min = st.sidebar.slider("PAT CAGR min", -50.0, 75.0, key="pat_cagr_min", step=0.5)
opm_min = st.sidebar.slider("OPM min", -25.0, 60.0, key="opm_min", step=0.5)
pe_max = st.sidebar.slider("P/E max", 0.0, 200.0, key="pe_max", step=1.0)
pb_max = st.sidebar.slider("P/B max", 0.0, 50.0, key="pb_max", step=0.5)
dividend_yield_min = st.sidebar.slider("Dividend Yield min", 0.0, 10.0, key="dividend_yield_min", step=0.1)
icr_min = st.sidebar.slider("ICR min", 0.0, 50.0, key="icr_min", step=0.5)


def num(column: str, high_default: bool = False) -> pd.Series:
    fill = 10**9 if high_default else -10**9
    return pd.to_numeric(universe[column], errors="coerce").fillna(fill)


filtered = universe[
    (num("return_on_equity_pct") >= roe_min)
    & (num("debt_to_equity", high_default=True) <= de_max)
    & (num("free_cash_flow_cr") >= fcf_min)
    & (num("revenue_cagr_5yr") >= revenue_cagr_min)
    & (num("pat_cagr_5yr") >= pat_cagr_min)
    & (num("operating_profit_margin_pct") >= opm_min)
    & (num("pe_ratio", high_default=True) <= pe_max)
    & (num("pb_ratio", high_default=True) <= pb_max)
    & (num("dividend_yield") >= dividend_yield_min)
    & (num("interest_coverage") >= icr_min)
].copy()

visible_columns = [
    "ticker",
    "company_name",
    "broad_sector",
    "composite_quality_score",
    "return_on_equity_pct",
    "debt_to_equity",
    "free_cash_flow_cr",
    "revenue_cagr_5yr",
    "pat_cagr_5yr",
    "operating_profit_margin_pct",
    "pe_ratio",
    "pb_ratio",
    "dividend_yield",
    "interest_coverage",
]
results = filtered[visible_columns].rename(
    columns={
        "ticker": "company_id",
        "company_name": "name",
        "broad_sector": "sector",
        "composite_quality_score": "composite_score",
    }
)

st.subheader(f"{len(results)} companies match your filters")
st.download_button(
    "Download CSV",
    data=results.to_csv(index=False).encode("utf-8"),
    file_name="nifty100_screener_results.csv",
    mime="text/csv",
)
st.dataframe(display_na(results), width="stretch", hide_index=True)
