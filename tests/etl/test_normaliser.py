from src.etl.normaliser import (
    normalize_year,
    normalize_ticker,
    normalize_company_name,
    normalize_number,
    normalize_text,
)


def test_normalize_year():
    assert normalize_year("FY2024") == 2024
    assert normalize_year("2023-24") == 2023
    assert normalize_year(2022) == 2022


def test_normalize_ticker():
    assert normalize_ticker(" tcs ") == "TCS"
    assert normalize_ticker("infy") == "INFY"


def test_normalize_company_name():
    assert normalize_company_name(" tata consultancy services ") == "Tata Consultancy Services"


def test_normalize_number():
    assert normalize_number("1,25,500") == 125500.0
    assert normalize_number(100) == 100.0


def test_normalize_text():
    assert normalize_text(" Hello     World ") == "Hello World"