from pathlib import Path 
"""
validator.py

Data Quality (DQ) validation functions
for the Nifty100 Data Foundation project.
"""

import pandas as pd


def validate_dq01_company_pk(df):
    """
    DQ-01:
    Check that company_id is unique.

    Returns:
        DataFrame containing duplicate company_id rows.
        Empty DataFrame means PASS.
    """

    duplicates = df[df.duplicated(subset=["company_id"], keep=False)]

    return duplicates

def validate_dq02_company_year_unique(df):
    """
    DQ-02:
    Check that (company_id, year) is unique.

    Returns:
        DataFrame containing duplicate
        company_id + year combinations.
    """

    duplicates = df[df.duplicated(
        subset=["company_id", "year"],
        keep=False
    )]

    return duplicates

def validate_dq03_foreign_key(companies_df, financial_df):
    """
    DQ-03:
    Check that every company_id in the financial table
    exists in the companies table.

    Returns:
        DataFrame containing invalid foreign keys.
    """

    valid_company_ids = set(companies_df["company_id"])

    invalid_rows = financial_df[
        ~financial_df["company_id"].isin(valid_company_ids)
    ]

    return invalid_rows

def validate_dq04_balance_sheet(df):
    """
    DQ-04:
    Check that Total Assets and Total Liabilities
    are balanced within 1%.

    Returns:
        DataFrame containing rows that fail the check.
    """

    if "total_assets" not in df.columns or "total_liabilities" not in df.columns:
        raise KeyError("Required columns: total_assets, total_liabilities")

    tolerance = 0.01  # 1%

    difference = (
        (df["total_assets"] - df["total_liabilities"]).abs()
        / df["total_assets"]
    )

    failed_rows = df[difference > tolerance]

    return failed_rows

def validate_dq05_opm(df):
    """
    DQ-05:
    Validate Operating Profit Margin (OPM).

    Formula:
        OPM = (Operating Profit / Sales) * 100

    Returns:
        DataFrame containing rows where calculated OPM
        differs from reported OPM by more than 1%.
    """

    required_columns = [
        "sales",
        "operating_profit",
        "opm"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(f"Missing required column: {column}")

    calculated_opm = (
        df["operating_profit"] / df["sales"]
    ) * 100

    difference = (calculated_opm - df["opm"]).abs()

    failed_rows = df[difference > 1]

    return failed_rows

def validate_dq06_positive_sales(df):
    """
    DQ-06:
    Check that sales are greater than zero.

    Returns:
        DataFrame containing rows where sales <= 0.
    """

    if "sales" not in df.columns:
        raise KeyError("Missing required column: sales")

    failed_rows = df[df["sales"] <= 0]

    return failed_rows

def validate_dq07_net_cash(df):
    """
    DQ-07:
    Validate Net Cash calculation.

    Formula:
        Net Cash = Cash - Total Debt

    Returns:
        DataFrame containing rows where the reported
        net_cash differs from the calculated value.
    """

    required_columns = [
        "cash",
        "total_debt",
        "net_cash"
    ]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(f"Missing required column: {column}")

    calculated_net_cash = df["cash"] - df["total_debt"]

    difference = (calculated_net_cash - df["net_cash"]).abs()

    failed_rows = df[difference > 1]

    return failed_rows

def validate_dq07_net_cash_flow(df):
    """
    DQ-07:
    Validate Net Cash Flow.

    Formula:
        Operating Activity +
        Investing Activity +
        Financing Activity =
        Net Cash Flow

    Returns:
        DataFrame containing rows where the calculated
        Net Cash Flow differs from the reported value.
    """

    required_columns = [
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
    ]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(f"Missing required column: {column}")

    calculated = (
        df["operating_activity"]
        + df["investing_activity"]
        + df["financing_activity"]
    )

    failed_rows = df[calculated != df["net_cash_flow"]]

    return failed_rows

def validate_dq08_tax_rate(df):
    """
    DQ-08:
    Validate Tax Percentage.

    Rule:
        Tax percentage must be between 0 and 100.

    Returns:
        DataFrame containing invalid tax percentages.
    """

    if "tax_percentage" not in df.columns:
        raise KeyError("Missing required column: tax_percentage")

    failed_rows = df[
        (df["tax_percentage"] < 0) |
        (df["tax_percentage"] > 100)
    ]

    return failed_rows

def validate_dq09_dividend_cap(df):
    """
    DQ-09:
    Validate Dividend Cap.

    Rule:
        Dividend payout should not exceed net profit.

    Returns:
        DataFrame containing invalid dividend payouts.
    """

    required_columns = [
        "dividend_payout",
        "net_profit",
    ]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(f"Missing required column: {column}")

    failed_rows = df[
        df["dividend_payout"] > df["net_profit"]
    ]

    return failed_rows

def validate_dq10_url(df):
    """
    DQ-10:
    Validate website URLs.

    Rule:
        Website must start with http:// or https://

    Returns:
        DataFrame containing invalid website URLs.
    """

    if "website" not in df.columns:
        raise KeyError("Missing required column: website")

    websites = df["website"].fillna("").astype(str).str.strip()

    failed_rows = df[
        (websites != "") &
        (~websites.str.startswith(("http://", "https://")))
    ]

    return failed_rows

def validate_dq11_eps_sign(df):
    """
    DQ-11:
    Validate EPS Sign.

    Rules:
        - Positive Net Profit => EPS should be >= 0
        - Negative Net Profit => EPS should be <= 0

    Returns:
        DataFrame containing invalid EPS values.
    """

    required_columns = ["net_profit", "eps"]

    for column in required_columns:
        if column not in df.columns:
            raise KeyError(f"Missing required column: {column}")

    failed_rows = df[
        ((df["net_profit"] > 0) & (df["eps"] < 0)) |
        ((df["net_profit"] < 0) & (df["eps"] > 0))
    ]

    return failed_rows

def validate_dq13_coverage(df):
    """
    DQ-13:
    Coverage Guide

    Every document must contain:
    company_id
    Year
    Annual_Report
    """

    required = [
        "company_id",
        "Year",
        "Annual_Report"
    ]

    failed_rows = df[
        df[required].isnull().any(axis=1)
    ]

    return failed_rows

def save_validation_failures(failures, output_file="output/validation_failures.csv"):
    """
    Save all validation failures to a CSV file.

    Parameters
    ----------
    failures : list[pd.DataFrame]
        List of DataFrames returned by DQ rules.

    output_file : str
        Output CSV file.
    """

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    valid_failures = [
        df for df in failures
        if df is not None and not df.empty
    ]

    if valid_failures:
        final_df = pd.concat(valid_failures, ignore_index=True)
        final_df.to_csv(output_path, index=False)
    else:
        pd.DataFrame().to_csv(output_path, index=False)