import sqlite3

import pandas as pd

from src.nlp.pros_cons_generator import (
    CON_RULES,
    PRO_RULES,
    generate_for_company,
    generate_pros_cons,
)


def _history() -> pd.DataFrame:
    rows = []
    for index, year in enumerate(range(2020, 2025)):
        rows.append(
            {
                "company_id": "ABC",
                "year": f"Mar {year}",
                "broad_sector": "Industrials",
                "return_on_equity_pct": 21.0 + index,
                "return_on_capital_employed_pct": 18.0,
                "free_cash_flow_cr": 10.0 + index,
                "debt_to_equity": 0.0 if year == 2024 else 0.1,
                "revenue_cagr_5yr": 16.0,
                "operating_profit_margin_pct": 26.0,
                "pat_cagr_5yr": 21.0,
                "interest_coverage": 11.0,
                "icr_label": None,
                "dividend_yield": 2.5,
                "eps_cagr_5yr": 16.0,
                "earnings_per_share": 10.0 + index,
                "dividend_payout_ratio_pct": 30.0,
                "net_debt_cr": 0.0,
                "sales": 100.0 + index * 10,
                "operating_profit": 20.0 + index * 2,
                "depreciation": 2.0,
                "net_profit": 10.0 + index,
                "eps": 10.0 + index,
                "dividend_payout": 30.0,
                "borrowings": 30.0 - index * 5,
                "total_assets": 100.0 + index * 20,
            }
        )
    return pd.DataFrame(rows)


def test_rule_sets_have_12_pros_and_12_cons():
    assert len(PRO_RULES) == 12
    assert len(CON_RULES) == 12


def test_generate_for_company_matches_named_pro_rules():
    result = generate_for_company(_history())

    matched_rules = set(result["rule_id"])

    assert {
        "PRO_01",
        "PRO_02",
        "PRO_03",
        "PRO_04",
        "PRO_05",
        "PRO_06",
        "PRO_07",
        "PRO_08",
        "PRO_09",
        "PRO_10",
        "PRO_11",
        "PRO_12",
    }.issubset(matched_rules)
    assert list(result.columns) == ["company_id", "type", "rule_id", "text", "confidence_pct"]
    assert result["confidence_pct"].gt(60).all()


def test_generate_for_company_matches_con_rules():
    history = _history().copy()
    history["return_on_equity_pct"] = [9.0, 8.0, 7.0, 6.0, 5.0]
    history["free_cash_flow_cr"] = [10.0, 11.0, -2.0, -3.0, -4.0]
    history["debt_to_equity"] = [0.1, 0.2, 0.4, 1.0, 2.5]
    history["revenue_cagr_5yr"] = 4.0
    history["operating_profit_margin_pct"] = [16.0, 15.0, 14.0, 13.0, 12.0]
    history["pat_cagr_5yr"] = -1.0
    history["interest_coverage"] = 1.0
    history["dividend_payout_ratio_pct"] = 120.0
    history["eps_cagr_5yr"] = -1.0
    history["earnings_per_share"] = [14.0, 13.0, 12.0, 11.0, 10.0]
    history["return_on_capital_employed_pct"] = 9.0
    history["net_debt_cr"] = 120.0
    history["operating_profit"] = 30.0
    history["depreciation"] = 5.0
    history["sales"] = [140.0, 130.0, 120.0, 110.0, 100.0]
    history["net_profit"] = [10.0, 8.0, 6.0, 4.0, -1.0]

    result = generate_for_company(history)

    assert {
        "CON_01",
        "CON_02",
        "CON_03",
        "CON_04",
        "CON_05",
        "CON_06",
        "CON_07",
        "CON_08",
        "CON_09",
        "CON_10",
        "CON_11",
        "CON_12",
    }.issubset(set(result["rule_id"]))
    assert result.loc[result["rule_id"].eq("CON_01"), "text"].str.contains("2.50").any()


def test_generate_pros_cons_writes_summary_from_database(tmp_path):
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE companies (id TEXT)")
        conn.execute("CREATE TABLE sectors (company_id TEXT, broad_sector TEXT)")
        conn.execute(
            """
            CREATE TABLE financial_ratios (
                company_id TEXT,
                year TEXT,
                return_on_equity_pct REAL,
                return_on_capital_employed_pct REAL,
                free_cash_flow_cr REAL,
                debt_to_equity REAL,
                revenue_cagr_5yr REAL,
                operating_profit_margin_pct REAL,
                pat_cagr_5yr REAL,
                interest_coverage REAL,
                icr_label TEXT,
                dividend_yield REAL,
                eps_cagr_5yr REAL,
                earnings_per_share REAL,
                dividend_payout_ratio_pct REAL,
                net_debt_cr REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE profitandloss (
                company_id TEXT,
                year INTEGER,
                sales REAL,
                operating_profit REAL,
                depreciation REAL,
                net_profit REAL,
                eps REAL,
                dividend_payout REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE balancesheet (
                company_id TEXT,
                year INTEGER,
                borrowings REAL,
                total_assets REAL
            )
            """
        )
        conn.execute("INSERT INTO companies VALUES ('ABC')")
        conn.execute("INSERT INTO sectors VALUES ('ABC', 'Industrials')")
        for row in _history().to_dict("records"):
            conn.execute(
                """
                INSERT INTO financial_ratios
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["company_id"],
                    row["year"],
                    row["return_on_equity_pct"],
                    row["return_on_capital_employed_pct"],
                    row["free_cash_flow_cr"],
                    row["debt_to_equity"],
                    row["revenue_cagr_5yr"],
                    row["operating_profit_margin_pct"],
                    row["pat_cagr_5yr"],
                    row["interest_coverage"],
                    row["icr_label"],
                    row["dividend_yield"],
                    row["eps_cagr_5yr"],
                    row["earnings_per_share"],
                    row["dividend_payout_ratio_pct"],
                    row["net_debt_cr"],
                ),
            )
            year = int(str(row["year"])[-4:])
            conn.execute(
                "INSERT INTO profitandloss VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    row["company_id"],
                    year,
                    row["sales"],
                    row["operating_profit"],
                    row["depreciation"],
                    row["net_profit"],
                    row["eps"],
                    row["dividend_payout"],
                ),
            )
            conn.execute(
                "INSERT INTO balancesheet VALUES (?, ?, ?, ?)",
                (row["company_id"], year, row["borrowings"], row["total_assets"]),
            )

    details, summary = generate_pros_cons(db_path=db_path, output_dir=tmp_path)

    assert not details.empty
    assert summary.loc[0, "company_id"] == "ABC"
    assert (tmp_path / "generated_pros_cons.csv").exists()
    assert (tmp_path / "generated_pros_cons_summary.csv").exists()
