import sqlite3
from pathlib import Path


def create_database(db_path=None):
    root = Path(__file__).resolve().parents[1]
    if db_path is None:
        db_path = root / "data" / "db" / "nifty100.db"
    else:
        db_path = Path(db_path)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)

    try:
        with open("db/schema.sql", "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        conn.commit()
    finally:
        conn.close()

    print(f"Database created successfully at {db_path}")
    return db_path


if __name__ == "__main__":
    create_database()