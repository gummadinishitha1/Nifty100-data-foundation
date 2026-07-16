"""
database_validator.py

Runs database quality checks for Nifty100 SQLite database.
"""

import sqlite3
from pathlib import Path
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_PATH = ROOT / "output" / "database_validation_report.csv"
FAILURE_PATH = ROOT / "output" / "validation_failures.csv"



# -----------------------------
# DQ-01 Primary Key Check
# -----------------------------

def check_duplicate_pk(conn, table, column="id"):

    query = f"""
    SELECT {column}, COUNT(*) cnt
    FROM {table}
    GROUP BY {column}
    HAVING cnt > 1;
    """

    df = pd.read_sql(query, conn)

    return len(df)



# -----------------------------
# DQ-02 Foreign Key Check
# -----------------------------

def check_foreign_key(
        conn,
        child_table,
        child_column,
        parent_table,
        parent_column):


    query = f"""
    SELECT COUNT(*)
    FROM {child_table}
    WHERE {child_column} NOT IN
    (
        SELECT {parent_column}
        FROM {parent_table}
    );
    """

    return conn.execute(query).fetchone()[0]



# -----------------------------
# DQ-03 NULL Check
# -----------------------------

def check_null_values(conn, table, column):

    query = f"""
    SELECT COUNT(*)
    FROM {table}
    WHERE {column} IS NULL;
    """

    return conn.execute(query).fetchone()[0]



# -----------------------------
# DQ-04 Balance Sheet Check
# -----------------------------

def check_balance_sheet(conn, failures):

    query = """

    SELECT
        company_id,
        year,
        total_assets,
        total_liabilities

    FROM balancesheet

    """

    df = pd.read_sql(query, conn)


    for _, row in df.iterrows():

        difference = abs(
            row["total_assets"]
            -
            row["total_liabilities"]
        )


        tolerance = max(
            abs(row["total_assets"]) * 0.01,
            1
        )


        if difference > tolerance:

            failures.append({

                "rule_id":"DQ-04",
                "table":"balancesheet",
                "column":"total_assets",
                "company_id":row["company_id"],
                "year":row["year"],
                "issue":
                f"Balance sheet mismatch difference={difference:.2f}",
                "severity":"CRITICAL"

            })



# -----------------------------
# DQ-05 OPM Validation
# -----------------------------

def check_opm(conn, failures):

    query = """

    SELECT
        company_id,
        year,
        sales,
        operating_profit,
        opm_percentage

    FROM profitandloss

    WHERE sales != 0

    """


    df = pd.read_sql(query, conn)


    for _, row in df.iterrows():

        calculated = (
            row["operating_profit"]
            /
            row["sales"]
        ) * 100


        difference = abs(
            calculated
            -
            row["opm_percentage"]
        )


        if difference > 1:


            failures.append({

                "rule_id":"DQ-05",
                "table":"profitandloss",
                "column":"opm_percentage",
                "company_id":row["company_id"],
                "year":row["year"],
                "issue":
                f"OPM mismatch calculated={calculated:.2f}, stored={row['opm_percentage']}",
                "severity":"WARNING"

            })



# -----------------------------
# DQ-06 Sales Growth Validation
# -----------------------------

def check_sales_growth(conn, failures):

    query = """

    SELECT
        company_id,
        year,
        sales

    FROM profitandloss

    ORDER BY company_id, year

    """


    df = pd.read_sql(query, conn)


    for company, group in df.groupby("company_id"):


        previous_sales = None


        for _, row in group.iterrows():


            current_sales = row["sales"]


            if previous_sales is not None and previous_sales != 0:


                growth = (
                    (current_sales - previous_sales)
                    /
                    previous_sales
                ) * 100


                if growth < -90 or growth > 500:


                    failures.append({

                        "rule_id":"DQ-06",
                        "table":"profitandloss",
                        "column":"sales",
                        "company_id":company,
                        "year":row["year"],
                        "issue":
                        f"Unusual sales growth {growth:.2f}%",
                        "severity":"WARNING"

                    })


            previous_sales = current_sales

# -----------------------------
# DQ-07 Negative Sales Check
# -----------------------------

def check_negative_sales(conn, failures):

    query = """

    SELECT
        company_id,
        year,
        sales

    FROM profitandloss

    """

    df = pd.read_sql(query, conn)

    for _, row in df.iterrows():

        if pd.notna(row["sales"]) and row["sales"] < 0:

            failures.append({

                "rule_id":"DQ-07",
                "table":"profitandloss",
                "column":"sales",
                "company_id":row["company_id"],
                "year":row["year"],
                "issue":f"Negative sales value ({row['sales']})",
                "severity":"CRITICAL"

            })

# -----------------------------
# DQ-08 Negative Operating Profit Check
# -----------------------------

def check_negative_operating_profit(conn, failures):

    query = """
    SELECT
        company_id,
        year,
        operating_profit
    FROM profitandloss
    WHERE operating_profit < 0;
    """

    df = pd.read_sql(query, conn)

    for _, row in df.iterrows():

        failures.append({

            "rule_id": "DQ-08",
            "table": "profitandloss",
            "column": "operating_profit",
            "company_id": row["company_id"],
            "year": row["year"],
            "issue": f"Negative operating profit ({row['operating_profit']})",
            "severity": "WARNING"

        })

# -----------------------------
# DQ-09 Negative Net Profit Check
# -----------------------------

def check_negative_net_profit(conn, failures):

    query = """
    SELECT
        company_id,
        year,
        net_profit
    FROM profitandloss
    WHERE net_profit < 0;
    """

    df = pd.read_sql(query, conn)

    for _, row in df.iterrows():

        failures.append({

            "rule_id": "DQ-09",
            "table": "profitandloss",
            "column": "net_profit",
            "company_id": row["company_id"],
            "year": row["year"],
            "issue": f"Negative net profit ({row['net_profit']})",
            "severity": "WARNING"

        })


# -----------------------------
# DQ-10 Net Cash Flow Validation
# -----------------------------

def check_net_cash_flow(conn, failures):

    query = """
    SELECT
        company_id,
        year,
        operating_activity,
        investing_activity,
        financing_activity,
        net_cash_flow
    FROM cashflow
    """

    df = pd.read_sql(query, conn)

    for _, row in df.iterrows():

        calculated = (
            row["operating_activity"]
            + row["investing_activity"]
            + row["financing_activity"]
        )

        difference = abs(
            calculated -
            row["net_cash_flow"]
        )

        if difference > 1:

            failures.append({

                "rule_id": "DQ-10",
                "table": "cashflow",
                "column": "net_cash_flow",
                "company_id": row["company_id"],
                "year": row["year"],
                "issue":
                    f"Net cash mismatch calculated={calculated:.2f}, stored={row['net_cash_flow']}",
                "severity": "WARNING"

            })

# -----------------------------
# DQ-11 Negative EPS Growth Check
# -----------------------------

def check_negative_eps(conn, failures):

    query = """
    SELECT
        company_id,
        year,
        eps_growth
    FROM financial_ratios
    """

    df = pd.read_sql(query, conn)

    # Convert text values to numeric
    df["eps_growth"] = pd.to_numeric(df["eps_growth"], errors="coerce")

    df = df[df["eps_growth"] < 0]

    for _, row in df.iterrows():

        failures.append({

            "rule_id": "DQ-11",
            "table": "financial_ratios",
            "column": "eps_growth",
            "company_id": row["company_id"],
            "year": row["year"],
            "issue": f"Negative EPS Growth ({row['eps_growth']})",
            "severity": "WARNING"

        })

# -----------------------------
# DQ-12 Dividend Yield Check
# -----------------------------

def check_dividend_yield(conn, failures):

    query = """
SELECT
    company_id,
    year,
    dividend_yield
FROM financial_ratios
WHERE CAST(dividend_yield AS REAL) > 1000
"""

    df = pd.read_sql(query, conn)

    df["dividend_yield"] = (
        df["dividend_yield"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
    )

    df["dividend_yield"] = pd.to_numeric(
        df["dividend_yield"],
        errors="coerce"
    )

    for _, row in df.iterrows():

        if pd.notna(row["dividend_yield"]) and row["dividend_yield"] > 1000:

            failures.append({

                "rule_id":"DQ-12",
                "table":"financial_ratios",
                "column":"dividend_yield",
                "company_id":row["company_id"],
                "year":row["year"],
                "issue":f"Unusually high dividend yield ({row['dividend_yield']}%)",
                "severity":"WARNING"

            })
 

# -----------------------------
# DQ-13 Annual Report URL Check
# -----------------------------

def check_annual_report_url(conn, failures):

    query = """
    SELECT
        id,
        company_id,
        Year,
        Annual_Report
    FROM documents
    """

    df = pd.read_sql(query, conn)


    for _, row in df.iterrows():

        url = row["Annual_Report"]


        if pd.isna(url):

            failures.append({

                "rule_id":"DQ-13",
                "table":"documents",
                "column":"Annual_Report",
                "company_id":row["company_id"],
                "year": row["Year"],
                "issue":"Invalid Annual Report URL",
                "severity":"WARNING"

            })

            continue


        url = str(url).strip()


        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):

            failures.append({

                "rule_id":"DQ-13",
                "table":"documents",
                "column":"annual_report",
                "company_id":row["company_id"],
                "year":row["Year"],
                "issue":f"Invalid URL format ({url})",
                "severity":"WARNING"

            })

# -----------------------------
# DQ-14 Stock Price OHLC Validation
# -----------------------------

def check_stock_price_ohlc(conn, failures):

    query = """
    SELECT
        id,
        company_id,
        date,
        open_price,
        high_price,
        low_price,
        close_price
    FROM stock_prices
    """

    df = pd.read_sql(query, conn)


    for _, row in df.iterrows():

        if (
            row["high_price"] < row["open_price"]
            or row["high_price"] < row["close_price"]
            or row["low_price"] > row["open_price"]
            or row["low_price"] > row["close_price"]
        ):

            failures.append({

                "rule_id":"DQ-14",
                "table":"stock_prices",
                "column":"OHLC",
                "company_id":row["company_id"],
                "year":row["date"],
                "issue":
                (
                    f"Invalid OHLC "
                    f"O={row['open_price']} "
                    f"H={row['high_price']} "
                    f"L={row['low_price']} "
                    f"C={row['close_price']}"
                ),
                "severity":"CRITICAL"

            })
# -----------------------------
# DQ-15 profitandloss  Year Coverage Validation
# -----------------------------
def check_year_coverage(conn, failures):

    query = """
    SELECT 
        company_id,
        COUNT(DISTINCT year) AS year_count,
        MIN(year) AS min_year,
        MAX(year) AS max_year
    FROM profitandloss
    GROUP BY company_id
    """

    df = pd.read_sql(query, conn)

    for _, row in df.iterrows():

        # Expected minimum coverage
        if row["year_count"] < 5:

            failures.append({
                "rule_id": "DQ-15",
                "table": "profitandloss",
                "column": "year",
                "company_id": row["company_id"],
                "year": None,
                "issue": f"Insufficient year coverage ({row['year_count']} years)",
                "severity": "WARNING"
            })
# -----------------------------
# DQ-16 multiple  Duplicate Company-Year Validation
# -----------------------------
def check_duplicate_company_year(conn, failures):

    tables = [
        "profitandloss",
        "balancesheet",
        "cashflow",
        "financial_ratios"
    ]

    for table in tables:

        query = f"""
        SELECT 
            company_id,
            year,
            COUNT(*) AS duplicate_count
        FROM {table}
        GROUP BY company_id, year
        HAVING COUNT(*) > 1
        """

        df = pd.read_sql(query, conn)

        for _, row in df.iterrows():

            failures.append({
                "rule_id": "DQ-16",
                "table": table,
                "column": "company_id,year",
                "company_id": row["company_id"],
                "year": row["year"],
                "issue": f"Duplicate company-year record ({row['duplicate_count']} records)",
                "severity": "WARNING"
            })
# -----------------------------
# Main Validation
# -----------------------------

def run_validation():

    conn = sqlite3.connect(DB_PATH)


    results = []

    failures = []



    # DQ-01
    tables = [

        "companies",
        "profitandloss",
        "balancesheet",
        "cashflow",
        "documents",
        "sectors",
        "stock_prices",
        "financial_ratios",
        "prosandcons"

    ]


    for table in tables:

        failed = check_duplicate_pk(conn, table)


        results.append({

            "rule_id":"DQ-01",
            "table":table,
            "check":"Duplicate Primary Key",
            "status":"PASS" if failed==0 else "FAIL",
            "failed_records":failed

        })



    # DQ-02

    fk_checks=[

        ("profitandloss","company_id","companies","id"),
        ("balancesheet","company_id","companies","id"),
        ("cashflow","company_id","companies","id"),
        ("sectors","company_id","companies","id"),
        ("stock_prices","company_id","companies","id"),
        ("financial_ratios","company_id","companies","id")

    ]


    for child,col,parent,pcol in fk_checks:

        failed = check_foreign_key(
            conn,
            child,
            col,
            parent,
            pcol
        )


        results.append({

            "rule_id":"DQ-02",
            "table":child,
            "check":"Foreign Key Integrity",
            "status":"PASS" if failed==0 else "FAIL",
            "failed_records":failed

        })



    # DQ-03

    null_checks=[

        ("companies","id"),
        ("companies","company_name"),
        ("profitandloss","company_id"),
        ("balancesheet","company_id"),
        ("cashflow","company_id")

    ]


    for table,column in null_checks:

        failed = check_null_values(
            conn,
            table,
            column
        )


        results.append({

            "rule_id":"DQ-03",
            "table":table,
            "check":f"NULL check - {column}",
            "status":"PASS" if failed==0 else "WARNING",
            "failed_records":failed

        })



    # DQ-04

    check_balance_sheet(
        conn,
        failures
    )


    results.append({

        "rule_id":"DQ-04",
        "table":"balancesheet",
        "check":"Assets = Liabilities",
        "status":"PASS" if not any(
            x["rule_id"]=="DQ-04"
            for x in failures
        )
        else "FAIL",
        "failed_records":sum(
            1 for x in failures
            if x["rule_id"]=="DQ-04"
        )

    })



    # DQ-05

    check_opm(
        conn,
        failures
    )


    results.append({

        "rule_id":"DQ-05",
        "table":"profitandloss",
        "check":"Operating Profit Margin Cross Check",
        "status":"PASS" if not any(
            x["rule_id"]=="DQ-05"
            for x in failures
        )
        else "WARNING",
        "failed_records":sum(
            1 for x in failures
            if x["rule_id"]=="DQ-05"
        )

    })



    # DQ-06

    check_sales_growth(
        conn,
        failures
    )


    results.append({

        "rule_id":"DQ-06",
        "table":"profitandloss",
        "check":"Sales Growth Validation",
        "status":"PASS" if not any(
            x["rule_id"]=="DQ-06"
            for x in failures
        )
        else "WARNING",
        "failed_records":sum(
            1 for x in failures
            if x["rule_id"]=="DQ-06"
        )

    })

        # DQ-07

    check_negative_sales(
        conn,
        failures
    )

    results.append({

        "rule_id":"DQ-07",
        "table":"profitandloss",
        "check":"Negative Sales Check",
        "status":"PASS" if not any(
            x["rule_id"]=="DQ-07"
            for x in failures
        )
        else "FAIL",
        "failed_records":sum(
            1 for x in failures
            if x["rule_id"]=="DQ-07"
        )

    })

    # DQ-08

    check_negative_operating_profit(
    conn,
    failures
)

    results.append({

    "rule_id":"DQ-08",
    "table":"profitandloss",
    "check":"Negative Operating Profit Check",
    "status":"PASS" if not any(
        x["rule_id"]=="DQ-08"
        for x in failures
    )
    else "WARNING",
    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-08"
    )

})
    
    # DQ-09

    check_negative_net_profit(
    conn,
    failures
)

    results.append({

    "rule_id":"DQ-09",
    "table":"profitandloss",
    "check":"Negative Net Profit Check",
    "status":"PASS" if not any(
        x["rule_id"]=="DQ-09"
        for x in failures
    )
    else "WARNING",
    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-09"
    )

})
    # DQ-10

    check_net_cash_flow(
    conn,
    failures
)

    results.append({

    "rule_id":"DQ-10",
    "table":"cashflow",
    "check":"Net Cash Flow Validation",
    "status":"PASS" if not any(
        x["rule_id"]=="DQ-10"
        for x in failures
    )
    else "WARNING",
    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-10"
    )

})
    
    # DQ-11

    check_negative_eps(
    conn,
    failures
)

    results.append({

    "rule_id":"DQ-11",
    "table":"financial_ratios",
    "check":"Negative EPS Check",
    "status":"PASS" if not any(
        x["rule_id"]=="DQ-11"
        for x in failures
    )
    else "WARNING",
    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-11"
    )

})
    
    # DQ-12

    check_dividend_yield(
    conn,
    failures
)

    results.append({

    "rule_id":"DQ-12",
    "table":"financial_ratios",
    "check":"Dividend Yield Check",
    "status":"PASS" if not any(
        x["rule_id"]=="DQ-12"
        for x in failures
    )
    else "WARNING",
    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-12"
    )

})
    
        # DQ-13

    check_annual_report_url(
        conn,
        failures
    )


    results.append({

        "rule_id":"DQ-13",
        "table":"documents",
        "check":"Annual Report URL Check",
        "status":"PASS" if not any(
            x["rule_id"]=="DQ-13"
            for x in failures
        )
        else "WARNING",
        "failed_records":sum(
            1 for x in failures
            if x["rule_id"]=="DQ-13"
        )

    })

        # DQ-14

    check_stock_price_ohlc(
        conn,
        failures
    )


    results.append({

        "rule_id":"DQ-14",
        "table":"stock_prices",
        "check":"OHLC Validation",
        "status":"PASS" if not any(
            x["rule_id"]=="DQ-14"
            for x in failures
)
    else "WARNING",
        "failed_records":sum(
            1 for x in failures
            if x["rule_id"]=="DQ-14"
        )

    })

    # DQ-15

    check_year_coverage(
        conn,
        failures
)


    results.append({

    "rule_id":"DQ-15",
    "table":"profitandloss",
    "check":"Year Coverage Validation",

    "status":"PASS" if not any(
        x["rule_id"]=="DQ-15"
        for x in failures
    )
    else "WARNING",

    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-15"
    )

})
    
    # DQ-16

    check_duplicate_company_year(
    conn,
    failures
)


    results.append({

    "rule_id":"DQ-16",
    "table":"multiple",
    "check":"Duplicate Company-Year Validation",

    "status":"PASS" if not any(
        x["rule_id"]=="DQ-16"
        for x in failures
    )
    else "WARNING",

    "failed_records":sum(
        1 for x in failures
        if x["rule_id"]=="DQ-16"
    )

})

    conn.close()



    OUTPUT_DIR = ROOT / "output"
    OUTPUT_DIR.mkdir(
        exist_ok=True
    )


    failure_columns = [
        "rule_id",
        "table",
        "column",
        "company_id",
        "year",
        "issue",
        "severity",
    ]

    pd.DataFrame(failures, columns=failure_columns).to_csv(
        FAILURE_PATH,
        index=False
    )


    report = pd.DataFrame(results)


    report.to_csv(
        OUTPUT_PATH,
        index=False
    )


    print("Validation completed successfully!")
    print(
        f"Rules executed: {len(report)} | "
        f"Failures/warnings: {len(failures)}"
    )
    print(report)



if __name__ == "__main__":

    run_validation()
