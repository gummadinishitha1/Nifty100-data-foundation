import sqlite3
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database import create_database


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"

FILES = {
    "companies": ROOT / "data" / "raw" / "companies.xlsx",
    "profitandloss": ROOT / "data" / "raw" / "profitandloss.xlsx",
    "balancesheet": ROOT / "data" / "raw" / "balancesheet.xlsx",
    "cashflow": ROOT / "data" / "raw" / "cashflow.xlsx",
    "analysis": ROOT / "data" / "raw" / "analysis.xlsx",
    "documents": ROOT / "data" / "raw" / "documents.xlsx",
    "prosandcons": ROOT / "data" / "raw" / "prosandcons.xlsx",
    "sectors": ROOT / "data" / "raw" / "sectors.xlsx",
    "stock_prices": ROOT / "data" / "raw" / "stock_prices.xlsx",
    "financial_ratios": ROOT / "data" / "raw" / "financial_ratios.xlsx",
    "market_cap": ROOT / "data" / "raw" / "market_cap.xlsx",
    "peer_groups": ROOT / "data" / "raw" / "peer_groups.xlsx",
}


YEAR_TABLES = [
    "profitandloss",
    "balancesheet",
    "cashflow",
    "financial_ratios"
]


def clean_datatypes(df):

    if "id" in df.columns:
        df["id"] = (
            df["id"]
            .astype(str)
            .str.strip()
        )

    if "company_id" in df.columns:
        df["company_id"] = (
            df["company_id"]
            .astype(str)
            .str.strip()
            .str.upper()
        )

    return df



def normalize_company_ids(df, table_name):
    """Align company identifiers to the companies table values."""

    if "company_id" not in df.columns:
        return df

    if table_name == "sectors":
        mapping = {
            "ADANIENT": "ADANIENT",
            "ADANIPORTS": "ADANIPORTS",
            "AXISBANK": "AXISBANK",
            "BAJAJFINSV": "BAJAJFINSV",
            "BHARTIARTL": "BHARTIARTL",
            "BPCL": "BPCL",
            "BRITANNIA": "BRITANNIA",
            "CIPLA": "CIPLA",
            "COALINDIA": "COALINDIA",
            "DIVISLAB": "DIVISLAB",
            "DRREDDY": "DRREDDY",
            "EICHERMOT": "EICHERMOT",
            "GRASIM": "GRASIM",
            "HCLTECH": "HCLTECH",
            "HDFCBANK": "HDFCBANK",
            "HEROMOTOCO": "HEROMOTOCO",
            "HINDALCO": "HINDALCO",
            "HINDUNILVR": "HINDUNILVR",
            "ICICIBANK": "ICICIBANK",
            "INDUSINDBK": "INDUSINDBK",
            "INFY": "INFY",
            "ITC": "ITC",
            "JSWSTEEL": "JSWSTEEL",
            "KOTAKBANK": "KOTAKBANK",
            "LT": "LT",
            "M&M": "MM",
            "MARUTI": "MARUTI",
            "NESTLEIND": "NESTLEIND",
            "NTPC": "NTPC",
            "ONGC": "ONGC",
            "POWERGRID": "POWERGRID",
            "RELIANCE": "RELIANCE",
            "SBILIFE": "SBILIFE",
            "SHRIRAMFIN": "SHRIRAMFIN",
            "SUNPHARMA": "SUNPHARMA",
            "TATACONSUM": "TATACONSUM",
            "TATAMOTORS": "TATAMOTORS",
            "TATASTEEL": "TATASTEEL",
            "TCS": "TCS",
            "TECHM": "TECHM",
            "TITAN": "TITAN",
            "ULTRACEMCO": "ULTRACEMCO",
            "UPL": "UPL",
            "WIPRO": "WIPRO",
            "ZEEL": "ZEEL",
        }
        df["company_id"] = df["company_id"].replace(mapping)
        return df

    mapping = {
        "M&M": "MM",
        "HDFCBANK": "HDFCBANK",
        "HCLTECH": "HCLTECH",
        "SBILIFE": "SBILIFE",
        "TATAMOTORS": "TATAMOTORS",
        "TATASTEEL": "TATASTEEL",
        "WIPRO": "WIPRO",
        "ZEEL": "ZEEL",
        "ULTRACEMCO": "ULTRACEMCO",
    }
    df["company_id"] = df["company_id"].replace(mapping)
    return df


def remove_duplicates(df, table_name):

    if table_name in YEAR_TABLES:

        before = len(df)

        df = df.drop_duplicates(
            subset=[
                "company_id",
                "year"
            ],
            keep="first"
        )

        if {"operating_profit", "sales", "opm_percentage"}.issubset(df.columns):
            df["opm_percentage"] = (
                (df["operating_profit"] / df["sales"]) * 100
            ).round(2)
            print("profitandloss: OPM recalculated")

        after = len(df)

        print(
            f"{table_name}: removed {before-after} duplicates"
        )


    return df



def read_excel_file(path, table_name):

    if table_name == "sectors":

        df = pd.read_excel(
            path,
            header=None
        )

        df.columns = [
            "id",
            "company_id",
            "broad_sector",
            "sub_sector",
            "index_weight_pct",
            "market_cap_category"
        ]

        df = df.iloc[1:].reset_index(drop=True)


    elif table_name == "financial_ratios":

        df = pd.read_excel(
            path,
            header=None
        )

        df.columns = [
            "id",
            "company_id",
            "year",
            "pe_ratio",
            "pb_ratio",
            "dividend_yield",
            "roe",
            "roce",
            "debt_to_equity",
            "interest_coverage",
            "sales_growth",
            "profit_growth",
            "eps_growth",
            "opm",
            "npm",
            "other_ratio"
        ]

        df = df.iloc[1:].reset_index(drop=True)


    elif table_name == "stock_prices":

        df = pd.read_excel(
            path,
            header=None
        )

        df.columns = [
            "id",
            "company_id",
            "date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "volume",
            "adjusted_close"
        ]

        df = df.iloc[1:].reset_index(drop=True)

    elif table_name == "market_cap":

        df = pd.read_excel(
            path,
            header=None
        )

        df.columns = [
            "id",
            "company_id",
            "year",
            "market_cap_crore",
            "enterprise_value_crore",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct"
        ]

        df = df.iloc[1:].reset_index(drop=True)

    elif table_name == "peer_groups":

        df = pd.read_excel(
            path,
            header=None
        )

        df.columns = [
            "id",
            "peer_group_name",
            "company_id",
            "is_benchmark"
        ]

        df = df.iloc[1:].reset_index(drop=True)

    else:

        df = pd.read_excel(
            path,
            header=1
        )


    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ","_")
    )


    df = clean_datatypes(df)
    df = normalize_company_ids(df, table_name)

    df = remove_duplicates(
        df,
        table_name
    )

    return df



def sync_missing_companies(conn):
    """Keep the companies table aligned to the source workbook and any
    canonical IDs that appear in financial tables.
    """

    existing = pd.read_sql("SELECT id FROM companies", conn)
    if existing.empty:
        print("No companies loaded yet")
        return

    company_ids = set(existing["id"])
    extra_ids = []

    for table_name in [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "financial_ratios",
        "sectors",
        "stock_prices",
        "analysis",
        "market_cap",
        "peer_groups",
    ]:
        ids = pd.read_sql_query(f"SELECT DISTINCT company_id FROM {table_name}", conn)
        extra_ids.extend(ids["company_id"].dropna().tolist())

    missing = sorted(set(extra_ids) - company_ids)
    if missing:
        missing_df = pd.DataFrame(
            {
                "id": missing,
                "company_name": missing,
            }
        )
        missing_df.to_sql("companies", conn, if_exists="append", index=False)
        print(f"Added missing companies: {missing}")

    print(
        f"Companies table contains {len(pd.read_sql_query('SELECT id FROM companies', conn))} records"
    )



def load_database():

    create_database(DB_PATH)

    conn = sqlite3.connect(
        DB_PATH
    )

    audit = []


    for table_name, file_path in FILES.items():

        path = Path(file_path)


        if not path.exists():

            print(
                f"Skipping {table_name}"
            )

            continue


        df = read_excel_file(
            path,
            table_name
        )


        print(
            "\nLoading:",
            table_name
        )

        print(
            df.head()
        )


        df.to_sql(
            table_name,
            conn,
            if_exists="append",
            index=False
        )


        audit.append(
            {
                "table": table_name,
                "rows_loaded": len(df),
                "rejections": 0,
                "critical_rejections": 0,
                "status": "SUCCESS"
            }
        )


        print(
            f"Loaded {table_name}: {len(df)} rows"
        )


    sync_missing_companies(
        conn
    )


    conn.commit()

    conn.close()


    OUTPUT_DIR.mkdir(
        exist_ok=True
    )


    pd.DataFrame(audit).to_csv(
        OUTPUT_DIR / "load_audit.csv",
        index=False
    )


    print(
        "\nLoad completed successfully!"
    )
    print(
        f"Tables loaded: {len(audit)} | "
        f"Rows loaded: {sum(item['rows_loaded'] for item in audit)}"
    )



if __name__ == "__main__":
    load_database()
