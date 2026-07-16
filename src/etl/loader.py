"""
loader.py

Reads Excel files and performs basic data cleaning.
"""

from pathlib import Path
import pandas as pd

from src.etl.normaliser import (
    normalize_year,
    normalize_ticker,
    normalize_company_name,
)


def load_excel(file_path):
    """
    Load an Excel file into a pandas DataFrame.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} not found.")

    df = pd.read_excel(file_path)

    return df


def clean_columns(df):
    """
    Standardize column names.
    """

    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
    )

    return df


def normalize_dataframe(df):
    """
    Normalize common columns if they exist.
    """

    if "year" in df.columns:
        df["year"] = df["year"].apply(normalize_year)

    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].apply(normalize_ticker)

    if "company_name" in df.columns:
        df["company_name"] = df["company_name"].apply(normalize_company_name)

    return df


def process_excel(file_path):
    """
    Complete ETL for one Excel file.
    """

    df = load_excel(file_path)
    df = clean_columns(df)
    df = normalize_dataframe(df)

    return df