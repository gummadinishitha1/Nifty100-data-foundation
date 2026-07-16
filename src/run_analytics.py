"""Simple analytics entry point for the Nifty100 data foundation."""

from pathlib import Path
import sqlite3


DB_PATH = Path("data/db/nifty100.db")
OUTPUT_DIR = Path("output")


def run_analytics() -> None:
    """Placeholder analytics runner for the current sprint."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

    print(f"Analytics ready. Database contains {table_count} tables.")


if __name__ == "__main__":
    run_analytics()