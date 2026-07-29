"""Display formatting helpers for Streamlit pages."""

from __future__ import annotations

import numpy as np
import pandas as pd


def display_na(df: pd.DataFrame) -> pd.DataFrame:
    """Return a display copy with missing and infinite values shown as N/A."""
    clean = df.copy()
    clean = clean.replace([np.inf, -np.inf], np.nan)
    return clean.astype(object).where(pd.notna(clean), "N/A")


def fmt_num(value: object, suffix: str = "", decimals: int = 2) -> str:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return f"{number:,.{decimals}f}{suffix}" if pd.notna(number) else "N/A"


def fmt_pct(value: object, decimals: int = 1) -> str:
    return fmt_num(value, "%", decimals)
