import sqlite3
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.database import create_database


def test_create_database_creates_expected_tables():
    tmp_dir = Path(".pytest_tmp_local")
    tmp_dir.mkdir(exist_ok=True)
    db_path = tmp_dir / f"test_nifty100_{uuid4().hex}.db"

    try:
        create_database(db_path)

        conn = sqlite3.connect(db_path)
        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            conn,
        )
        conn.close()
    finally:
        db_path.unlink(missing_ok=True)

    table_names = set(tables["name"])

    assert "companies" in table_names
    assert "profitandloss" in table_names
    assert "balancesheet" in table_names
    assert "stock_prices" in table_names
