"""Parse text metrics from the raw analysis workbook."""

from __future__ import annotations

from pathlib import Path
import re
import sqlite3

import pandas as pd

from src.analytics.cagr import fiscal_year_sort_key


ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_PATH = ROOT / "data" / "raw" / "analysis.xlsx"
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
PARSED_CSV = OUTPUT_DIR / "analysis_parsed.csv"
FAILURES_CSV = OUTPUT_DIR / "parse_failures.csv"
VALIDATION_FLAGS_CSV = OUTPUT_DIR / "analysis_validation_flags.csv"

TEXT_FIELDS = (
    "compounded_sales_growth",
    "compounded_profit_growth",
    "stock_price_cagr",
    "roe",
)
ANALYSIS_PATTERN = re.compile(r"(\d+)\s*Years?:?\s*([\d.]+)%")
CAGR_RATIO_COLUMNS = {
    "compounded_sales_growth": "revenue_cagr_{years}yr",
    "compounded_profit_growth": "pat_cagr_{years}yr",
}


def _read_analysis_workbook(path: Path) -> pd.DataFrame:
    """Read the Analysis sheet, accounting for the exported title row."""
    df = pd.read_excel(path, sheet_name="Analysis", header=1)
    required = {"company_id", *TEXT_FIELDS}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"analysis workbook missing columns: {sorted(missing)}")
    return df


def parse_metric_text(text: object) -> tuple[int, float] | None:
    """Extract period and percent value using the Sprint 5 regex."""
    if pd.isna(text):
        return None
    match = ANALYSIS_PATTERN.search(str(text))
    if not match:
        return None
    return int(match.group(1)), float(match.group(2))


def parse_analysis_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    parsed_rows: list[dict[str, object]] = []
    failure_rows: list[dict[str, object]] = []

    for row in df.itertuples(index=False):
        company_id = getattr(row, "company_id")
        for metric_type in TEXT_FIELDS:
            source_text = getattr(row, metric_type)
            parsed = parse_metric_text(source_text)
            if parsed is None:
                failure_rows.append(
                    {
                        "company_id": company_id,
                        "metric_type": metric_type,
                        "source_text": source_text,
                        "reason": "regex_no_match",
                    }
                )
                continue

            period_years, value_pct = parsed
            parsed_rows.append(
                {
                    "company_id": company_id,
                    "metric_type": metric_type,
                    "period_years": period_years,
                    "value_pct": value_pct,
                }
            )

    return pd.DataFrame(
        parsed_rows,
        columns=["company_id", "metric_type", "period_years", "value_pct"],
    ), pd.DataFrame(
        failure_rows,
        columns=["company_id", "metric_type", "source_text", "reason"],
    )


def _latest_ratio_rows(db_path: Path) -> pd.DataFrame:
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)

    if ratios.empty:
        return ratios

    frames = []
    for _, group in ratios.groupby("company_id", sort=False):
        group = group.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key))
        frames.append(group.tail(1))
    return pd.concat(frames, ignore_index=True)


def validate_against_ratio_engine(
    parsed: pd.DataFrame,
    db_path: Path = DB_PATH,
    tolerance_pct: float = 5.0,
) -> pd.DataFrame:
    """Flag parsed sales/profit CAGR values that diverge from computed ratios."""
    latest = _latest_ratio_rows(db_path)
    if parsed.empty or latest.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "metric_type",
                "period_years",
                "parsed_value_pct",
                "computed_value_pct",
                "divergence_pct",
                "ratio_year",
                "ratio_column",
            ]
        )

    latest_by_company = latest.set_index("company_id")
    flags: list[dict[str, object]] = []

    for row in parsed.itertuples(index=False):
        column_template = CAGR_RATIO_COLUMNS.get(row.metric_type)
        if column_template is None:
            continue

        ratio_column = column_template.format(years=row.period_years)
        if ratio_column not in latest_by_company.columns or row.company_id not in latest_by_company.index:
            continue

        ratio_row = latest_by_company.loc[row.company_id]
        computed = ratio_row.get(ratio_column)
        if pd.isna(computed):
            continue

        divergence = abs(float(row.value_pct) - float(computed))
        if divergence > tolerance_pct:
            flags.append(
                {
                    "company_id": row.company_id,
                    "metric_type": row.metric_type,
                    "period_years": row.period_years,
                    "parsed_value_pct": row.value_pct,
                    "computed_value_pct": float(computed),
                    "divergence_pct": divergence,
                    "ratio_year": ratio_row.get("year"),
                    "ratio_column": ratio_column,
                }
            )

    return pd.DataFrame(
        flags,
        columns=[
            "company_id",
            "metric_type",
            "period_years",
            "parsed_value_pct",
            "computed_value_pct",
            "divergence_pct",
            "ratio_year",
            "ratio_column",
        ],
    )


def parse_analysis(
    analysis_path: Path = ANALYSIS_PATH,
    output_dir: Path = OUTPUT_DIR,
    db_path: Path = DB_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Parse analysis.xlsx and write Sprint 5 Day 29 CSV outputs."""
    output_dir.mkdir(exist_ok=True)
    analysis = _read_analysis_workbook(analysis_path)
    parsed, failures = parse_analysis_rows(analysis)
    validation_flags = validate_against_ratio_engine(parsed, db_path=db_path)

    parsed.to_csv(output_dir / PARSED_CSV.name, index=False)
    failures.to_csv(output_dir / FAILURES_CSV.name, index=False)
    validation_flags.to_csv(output_dir / VALIDATION_FLAGS_CSV.name, index=False)
    return parsed, failures, validation_flags


def main() -> None:
    parsed, failures, validation_flags = parse_analysis()
    print(f"Wrote {PARSED_CSV}: {len(parsed)} rows")
    print(f"Wrote {FAILURES_CSV}: {len(failures)} rows")
    print(f"Wrote {VALIDATION_FLAGS_CSV}: {len(validation_flags)} rows")


if __name__ == "__main__":
    main()
