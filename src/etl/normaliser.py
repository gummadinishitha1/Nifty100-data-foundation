"""
normaliser.py

Utility functions for cleaning and standardising
financial data before loading into SQLite.
"""

import re
import pandas as pd


def normalize_year(year):
    """
    Convert different year formats into a 4-digit integer.

    Examples:
        FY2024 -> 2024
        2024-25 -> 2024
        2024 -> 2024
    """

    if pd.isna(year):
        return None

    year = str(year).strip()

    match = re.search(r"(20\d{2}|19\d{2})", year)

    if match:
        return int(match.group())

    return None


def normalize_ticker(ticker):
    """
    Convert ticker symbols into uppercase without spaces.
    """

    if pd.isna(ticker):
        return None

    ticker = str(ticker).strip().upper()

    ticker = ticker.replace(" ", "")

    return ticker


def normalize_company_name(name):
    """
    Standardize company names.
    """

    if pd.isna(name):
        return None

    name = str(name).strip()

    name = re.sub(r"\s+", " ", name)

    return name.title()


def normalize_number(value):
    """
    Convert numbers stored as strings into float.

    Handles:
    1,234
    5,000.25
    """

    if pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).replace(",", "").strip()

    try:
        return float(value)
    except ValueError:
        return None


def normalize_text(text):
    """
    Remove extra whitespace.
    """

    if pd.isna(text):
        return None

    text = str(text).strip()

    text = re.sub(r"\s+", " ", text)

    return text


if __name__ == "__main__":
    print(normalize_year("FY2024"))
    print(normalize_ticker(" infy "))
    print(normalize_company_name(" tata consultancy services "))
    print(normalize_number("1,25,500"))
    print(normalize_text(" Hello     World "))