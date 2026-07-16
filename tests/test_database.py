import sqlite3

import pandas as pd

from src.database import create_database


def test_create_database_creates_expected_tables(tmp_path):
    db_path = tmp_path / "test_nifty100.db"

    create_database(db_path)

    conn = sqlite3.connect(db_path)
    tables = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        conn,
    )
    conn.close()

    table_names = set(tables["name"])

    assert "companies" in table_names
    assert "profitandloss" in table_names
    assert "balancesheet" in table_names
    assert "stock_prices" in table_names
