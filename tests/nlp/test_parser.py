import sqlite3

import pandas as pd

from src.nlp.parser import (
    parse_analysis_rows,
    parse_metric_text,
    validate_against_ratio_engine,
)


def test_parse_metric_text_accepts_year_variants():
    assert parse_metric_text("10 Years: 21%") == (10, 21.0)
    assert parse_metric_text("5 Years          14%") == (5, 14.0)
    assert parse_metric_text("1 Year: 16%") == (1, 16.0)


def test_parse_metric_text_rejects_ttm_last_year_and_negative_values():
    assert parse_metric_text("TTM: 43%") is None
    assert parse_metric_text("Last Year: 12%") is None
    assert parse_metric_text("3 Years: -1%") is None


def test_parse_analysis_rows_logs_failures():
    df = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "compounded_sales_growth": "10 Years: 21%",
                "compounded_profit_growth": "TTM: 18%",
                "stock_price_cagr": "3 Years: 7%",
                "roe": "Last Year: 12%",
            }
        ]
    )

    parsed, failures = parse_analysis_rows(df)

    assert parsed.to_dict("records") == [
        {
            "company_id": "ABC",
            "metric_type": "compounded_sales_growth",
            "period_years": 10,
            "value_pct": 21.0,
        },
        {
            "company_id": "ABC",
            "metric_type": "stock_price_cagr",
            "period_years": 3,
            "value_pct": 7.0,
        },
    ]
    assert failures["metric_type"].tolist() == ["compounded_profit_growth", "roe"]


def test_validate_against_ratio_engine_flags_large_divergence(tmp_path):
    db_path = tmp_path / "ratios.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE financial_ratios (
                company_id TEXT,
                year TEXT,
                revenue_cagr_5yr REAL,
                pat_cagr_5yr REAL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO financial_ratios
            VALUES ('ABC', 'Mar 2026', 12.0, 7.0)
            """
        )

    parsed = pd.DataFrame(
        [
            {
                "company_id": "ABC",
                "metric_type": "compounded_sales_growth",
                "period_years": 5,
                "value_pct": 20.0,
            },
            {
                "company_id": "ABC",
                "metric_type": "compounded_profit_growth",
                "period_years": 5,
                "value_pct": 9.0,
            },
        ]
    )

    flags = validate_against_ratio_engine(parsed, db_path=db_path)

    assert len(flags) == 1
    assert flags.loc[0, "ratio_column"] == "revenue_cagr_5yr"
    assert flags.loc[0, "divergence_pct"] == 8.0
