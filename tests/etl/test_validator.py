import pandas as pd

from src.etl.validator import (
    validate_dq01_company_pk,
    validate_dq02_company_year_unique,
    validate_dq03_foreign_key,
    validate_dq04_balance_sheet,
    validate_dq05_opm,
    validate_dq06_positive_sales,
    validate_dq07_net_cash_flow,
    validate_dq08_tax_rate,
    validate_dq09_dividend_cap,
    validate_dq10_url,
    validate_dq11_eps_sign,validate_dq13_coverage,
)

def test_validate_dq01_company_pk_pass():
    """
    Test when all company_id values are unique.
    """

    df = pd.DataFrame(
        {
            "company_id": [1, 2, 3],
            "company_name": ["TCS", "Infosys", "Wipro"],
        }
    )

    result = validate_dq01_company_pk(df)

    assert result.empty


def test_validate_dq01_company_pk_fail():
    """
    Test when duplicate company_id values exist.
    """

    df = pd.DataFrame(
        {
            "company_id": [1, 2, 2],
            "company_name": ["TCS", "Infosys", "Reliance"],
        }
    )

    result = validate_dq01_company_pk(df)

    assert len(result) == 2

from src.etl.validator import validate_dq02_company_year_unique


def test_validate_dq02_pass():

    df = pd.DataFrame(
        {
            "company_id": [1, 1, 2],
            "year": [2023, 2024, 2024],
        }
    )

    result = validate_dq02_company_year_unique(df)

    assert result.empty


def test_validate_dq02_fail():

    df = pd.DataFrame(
        {
            "company_id": [1, 1, 2],
            "year": [2024, 2024, 2023],
        }
    )

    result = validate_dq02_company_year_unique(df)

    assert len(result) == 2

def test_validate_dq03_pass():

    companies = pd.DataFrame(
        {
            "company_id": [1, 2, 3]
        }
    )

    financial = pd.DataFrame(
        {
            "company_id": [1, 2],
            "year": [2024, 2024]
        }
    )

    result = validate_dq03_foreign_key(companies, financial)

    assert result.empty


def test_validate_dq03_fail():

    companies = pd.DataFrame(
        {
            "company_id": [1, 2]
        }
    )

    financial = pd.DataFrame(
        {
            "company_id": [1, 3],
            "year": [2024, 2024]
        }
    )

    result = validate_dq03_foreign_key(companies, financial)

    assert len(result) == 1
    assert result.iloc[0]["company_id"] == 3

def test_validate_dq04_pass():

    df = pd.DataFrame(
        {
            "total_assets": [1000, 2000],
            "total_liabilities": [995, 1990],  # within 1%
        }
    )

    result = validate_dq04_balance_sheet(df)

    assert result.empty


def test_validate_dq04_fail():

    df = pd.DataFrame(
        {
            "total_assets": [1000],
            "total_liabilities": [850],  # 15% difference
        }
    )

    result = validate_dq04_balance_sheet(df)

    assert len(result) == 1

def test_validate_dq05_pass():

    df = pd.DataFrame(
        {
            "sales": [1000],
            "operating_profit": [250],
            "opm": [25],
        }
    )

    result = validate_dq05_opm(df)

    assert result.empty


def test_validate_dq05_fail():

    df = pd.DataFrame(
        {
            "sales": [1000],
            "operating_profit": [250],
            "opm": [18],   # Incorrect OPM
        }
    )

    result = validate_dq05_opm(df)

    assert len(result) == 1

def test_validate_dq06_pass():

    df = pd.DataFrame(
        {
            "sales": [1000, 2500, 500]
        }
    )

    result = validate_dq06_positive_sales(df)

    assert result.empty


def test_validate_dq06_fail():

    df = pd.DataFrame(
        {
            "sales": [1000, 0, -250]
        }
    )

    result = validate_dq06_positive_sales(df)

    assert len(result) == 2

def test_validate_dq07_pass():

    df = pd.DataFrame(
        {
            "operating_activity": [100],
            "investing_activity": [-20],
            "financing_activity": [-30],
            "net_cash_flow": [50],
        }
    )

    result = validate_dq07_net_cash_flow(df)

    assert result.empty


def test_validate_dq07_fail():

    df = pd.DataFrame(
        {
            "operating_activity": [100],
            "investing_activity": [-20],
            "financing_activity": [-30],
            "net_cash_flow": [60],   # Incorrect
        }
    )

    result = validate_dq07_net_cash_flow(df)

    assert len(result) == 1


def test_validate_dq08_pass():

    df = pd.DataFrame(
        {
            "tax_percentage": [25, 18, 30]
        }
    )

    result = validate_dq08_tax_rate(df)

    assert result.empty


def test_validate_dq08_fail():

    df = pd.DataFrame(
        {
            "tax_percentage": [-5, 110]
        }
    )

    result = validate_dq08_tax_rate(df)

    assert len(result) == 2


def test_validate_dq09_pass():

    df = pd.DataFrame(
        {
            "dividend_payout": [50, 100],
            "net_profit": [200, 150],
        }
    )

    result = validate_dq09_dividend_cap(df)

    assert result.empty


def test_validate_dq09_fail():

    df = pd.DataFrame(
        {
            "dividend_payout": [250],
            "net_profit": [200],
        }
    )

    result = validate_dq09_dividend_cap(df)

    assert len(result) == 1


def test_validate_dq10_pass():

    df = pd.DataFrame(
        {
            "website": [
                "https://www.tcs.com",
                "http://example.com",
                "",
                None,
            ]
        }
    )

    result = validate_dq10_url(df)

    assert result.empty


def test_validate_dq10_fail():

    df = pd.DataFrame(
        {
            "website": [
                "www.tcs.com",
                "tcs.com",
            ]
        }
    )

    result = validate_dq10_url(df)

    assert len(result) == 2


def test_validate_dq11_pass():

    df = pd.DataFrame(
        {
            "net_profit": [500, -200],
            "eps": [25, -10],
        }
    )

    result = validate_dq11_eps_sign(df)

    assert result.empty


def test_validate_dq11_fail():

    df = pd.DataFrame(
        {
            "net_profit": [500, -200],
            "eps": [-25, 10],
        }
    )

    result = validate_dq11_eps_sign(df)

    assert len(result) == 2


def test_validate_dq13_pass():

    df = pd.DataFrame(
        {
            "company_id": ["ABB"],
            "Year": [2024],
            "Annual_Report": ["https://abc.com/report.pdf"]
        }
    )

    result = validate_dq13_coverage(df)

    assert result.empty


def test_validate_dq13_fail():

    df = pd.DataFrame(
        {
            "company_id": ["ABB"],
            "Year": [None],
            "Annual_Report": [None]
        }
    )

    result = validate_dq13_coverage(df)

    assert len(result) == 1