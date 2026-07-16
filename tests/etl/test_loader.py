import pandas as pd

from src.etl.loader import (
    clean_columns,
    normalize_dataframe,
)


def test_clean_columns():
    df = pd.DataFrame(
        columns=[
            "Company Name",
            "Year",
            "Ticker Symbol"
        ]
    )

    df = clean_columns(df)

    assert "company_name" in df.columns
    assert "year" in df.columns
    assert "ticker_symbol" in df.columns


def test_normalize_dataframe():
    df = pd.DataFrame(
        {
            "company_name": [" tata consultancy services "],
            "year": ["FY2024"],
            "ticker": [" tcs "],
        }
    )

    df = normalize_dataframe(df)

    assert df.loc[0, "company_name"] == "Tata Consultancy Services"
    assert df.loc[0, "year"] == 2024
    assert df.loc[0, "ticker"] == "TCS"