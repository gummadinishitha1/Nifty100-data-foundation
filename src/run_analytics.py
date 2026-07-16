"""Generate reusable analytics extracts from the Nifty100 database."""

from pathlib import Path
import sqlite3
import pandas as pd


DB_PATH = Path("data/db/nifty100.db")
OUTPUT_DIR = Path("output")

ANALYTICS_QUERIES = {
    "top10_sales_companies.csv": """
        SELECT
            company_id,
            year,
            sales,
            net_profit
        FROM profitandloss
        WHERE sales IS NOT NULL
        ORDER BY sales DESC
        LIMIT 10
    """,
    "profitability_ranking.csv": """
        SELECT
            company_id,
            year,
            net_profit,
            operating_profit,
            opm_percentage,
            eps
        FROM profitandloss
        WHERE net_profit IS NOT NULL
        ORDER BY net_profit DESC
        LIMIT 20
    """,
    "sector_analysis.csv": """
        SELECT
            s.broad_sector,
            COUNT(DISTINCT s.company_id) AS company_count,
            ROUND(AVG(c.roe_percentage), 2) AS avg_roe,
            ROUND(AVG(c.roce_percentage), 2) AS avg_roce
        FROM sectors s
        LEFT JOIN companies c
            ON c.id = s.company_id
        WHERE s.broad_sector IS NOT NULL
        GROUP BY s.broad_sector
        ORDER BY company_count DESC, s.broad_sector
    """,
}


def run_analytics() -> None:
    """Run analytics queries and save CSV outputs."""
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        table_count = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]

        print(f"Analytics ready. Database contains {table_count} tables.")

        for filename, query in ANALYTICS_QUERIES.items():
            output_path = OUTPUT_DIR / filename
            df = pd.read_sql_query(query, conn)
            df.to_csv(output_path, index=False)
            print(f"Wrote {filename}: {len(df)} rows")


if __name__ == "__main__":
    run_analytics()
