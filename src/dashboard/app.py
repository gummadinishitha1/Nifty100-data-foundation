"""Main Streamlit entry point for the Nifty 100 dashboard."""

from __future__ import annotations

from pathlib import Path
import runpy
import sys

import streamlit as st


APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


st.set_page_config(
    page_title="Nifty 100 Analytics",
    layout="wide",
    initial_sidebar_state="expanded",
)


PAGES = {
    "Home": "01_home.py",
    "Profile": "02_profile.py",
    "Screener": "03_screener.py",
    "Peers": "04_peers.py",
    "Trends": "05_trends.py",
    "Sectors": "06_sectors.py",
    "Capital": "07_capital.py",
    "Reports": "08_reports.py",
}


st.sidebar.title("Nifty 100 Analytics")
selected_page = st.sidebar.radio("Navigate", list(PAGES), label_visibility="collapsed")
runpy.run_path(str(APP_DIR / "pages" / PAGES[selected_page]), run_name="__streamlit_page__")
