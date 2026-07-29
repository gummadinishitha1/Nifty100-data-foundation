import requests
import streamlit as st

from utils.db import get_annual_reports, get_companies


st.title("Annual Reports")

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
reports = get_annual_reports(ticker)


@st.cache_data(ttl=3600, show_spinner=False)
def report_status(url: str) -> tuple[bool, str]:
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        if response.status_code == 405:
            response = requests.get(url, stream=True, allow_redirects=True, timeout=5)
        return response.status_code != 404 and response.status_code < 500, str(response.status_code)
    except requests.RequestException:
        return False, "unavailable"


if reports.empty:
    st.info("No annual report links available for this company.")
    st.stop()

st.subheader(f"{ticker} Annual Reports")
for row in reports.itertuples(index=False):
    ok, status = report_status(row.annual_report_url)
    year_col, link_col, status_col = st.columns([1, 4, 2])
    year_col.write(str(row.year))
    if ok:
        link_col.link_button("Open BSE PDF", row.annual_report_url, width="stretch")
        status_col.success(f"Available ({status})")
    else:
        link_col.write(row.annual_report_url)
        status_col.error("Report unavailable")
