"""Valuation summary generation for the Nifty 100 dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT_DIR = ROOT / "output"

MARKET_CAP_PATH = RAW_DIR / "market_cap.xlsx"
RATIOS_PATH = RAW_DIR / "financial_ratios.xlsx"
COMPANIES_PATH = RAW_DIR / "companies.xlsx"
SECTORS_PATH = RAW_DIR / "sectors.xlsx"

SUMMARY_PATH = OUTPUT_DIR / "valuation_summary.xlsx"
FLAGS_PATH = OUTPUT_DIR / "valuation_flags.csv"

SUMMARY_COLUMNS = [
    "company_id",
    "company_name",
    "sector",
    "P/E",
    "P/B",
    "EV/EBITDA",
    "FCF_yield_pct",
    "5yr_median_PE",
    "PE_vs_sector_median_pct",
    "flag",
]


def _read_excel_table(path: Path) -> pd.DataFrame:
    """Read raw files that may contain a title row before the real headers."""
    df = pd.read_excel(path)
    if "company_id" in df.columns:
        return df
    df = pd.read_excel(path, header=1)
    return df


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _fiscal_year(value: object) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip()
    if text.lower() == "ttm":
        return float("nan")
    year = pd.to_numeric(text[-4:], errors="coerce")
    return float(year) if pd.notna(year) else float("nan")


def _latest_by_company(df: pd.DataFrame, year_column: str = "year") -> pd.DataFrame:
    work = df.copy()
    work["_fiscal_year"] = work[year_column].map(_fiscal_year)
    work = work.dropna(subset=["company_id", "_fiscal_year"])
    work = work.sort_values(["company_id", "_fiscal_year"]).drop_duplicates("company_id", keep="last")
    return work.drop(columns=["_fiscal_year"])


def _five_year_median_pe(market_cap: pd.DataFrame, latest_year: int) -> pd.DataFrame:
    window_start = latest_year - 4
    history = market_cap.loc[
        market_cap["year"].between(window_start, latest_year, inclusive="both")
    ].copy()
    history["pe_ratio"] = _numeric(history["pe_ratio"])
    return (
        history.groupby("company_id", as_index=False)["pe_ratio"]
        .median()
        .rename(columns={"pe_ratio": "5yr_median_PE"})
    )


def _valuation_flag(pe_ratio: float, sector_median: float) -> str:
    if pd.isna(pe_ratio) or pd.isna(sector_median) or sector_median <= 0:
        return "Fair"
    if pe_ratio > sector_median * 1.5:
        return "Caution"
    if pe_ratio < sector_median * 0.7:
        return "Discount"
    return "Fair"


def build_valuation_summary() -> pd.DataFrame:
    """Build one latest-year valuation row per market-cap company."""
    market_cap = _read_excel_table(MARKET_CAP_PATH)
    ratios = _read_excel_table(RATIOS_PATH)
    companies = _read_excel_table(COMPANIES_PATH)
    sectors = _read_excel_table(SECTORS_PATH)

    market_cap["year"] = _numeric(market_cap["year"]).astype("Int64")
    for column in ["market_cap_crore", "pe_ratio", "pb_ratio", "ev_ebitda"]:
        market_cap[column] = _numeric(market_cap[column])

    latest_year = int(market_cap["year"].max())
    latest_market = (
        market_cap.loc[market_cap["year"].eq(latest_year)]
        .sort_values("company_id")
        .drop_duplicates("company_id", keep="last")
    )

    latest_ratios = _latest_by_company(ratios)
    latest_ratios["free_cash_flow_cr"] = _numeric(latest_ratios["free_cash_flow_cr"])

    sector_latest = latest_market.merge(
        sectors[["company_id", "broad_sector"]],
        on="company_id",
        how="left",
    )
    sector_medians = (
        sector_latest.groupby("broad_sector", dropna=False)["pe_ratio"]
        .median()
        .rename("sector_median_pe")
        .reset_index()
    )

    summary = (
        latest_market.merge(companies[["id", "company_name"]], left_on="company_id", right_on="id", how="left")
        .merge(sectors[["company_id", "broad_sector"]], on="company_id", how="left")
        .merge(latest_ratios[["company_id", "free_cash_flow_cr"]], on="company_id", how="left")
        .merge(_five_year_median_pe(market_cap, latest_year), on="company_id", how="left")
        .merge(sector_medians, on="broad_sector", how="left")
    )

    summary["FCF_yield_pct"] = summary["free_cash_flow_cr"] / summary["market_cap_crore"] * 100
    summary["PE_vs_sector_median_pct"] = (
        (summary["pe_ratio"] / summary["sector_median_pe"] - 1) * 100
    )
    summary["flag"] = [
        _valuation_flag(pe, median)
        for pe, median in zip(summary["pe_ratio"], summary["sector_median_pe"], strict=False)
    ]

    summary = summary.rename(
        columns={
            "broad_sector": "sector",
            "pe_ratio": "P/E",
            "pb_ratio": "P/B",
            "ev_ebitda": "EV/EBITDA",
        }
    )
    summary = summary[SUMMARY_COLUMNS].sort_values("company_id").reset_index(drop=True)

    numeric_columns = [
        "P/E",
        "P/B",
        "EV/EBITDA",
        "FCF_yield_pct",
        "5yr_median_PE",
        "PE_vs_sector_median_pct",
    ]
    summary[numeric_columns] = summary[numeric_columns].round(2)
    return summary


def write_valuation_outputs() -> tuple[Path, Path, pd.DataFrame]:
    """Write valuation summary and non-fair flags to output files."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    summary = build_valuation_summary()
    summary.to_excel(SUMMARY_PATH, index=False)

    flags = summary.loc[summary["flag"].isin(["Caution", "Discount"])].copy()
    flags.to_csv(FLAGS_PATH, index=False)
    return SUMMARY_PATH, FLAGS_PATH, summary


def main() -> None:
    summary_path, flags_path, summary = write_valuation_outputs()
    print(f"Wrote {summary_path}: {len(summary)} rows")
    print(f"Wrote {flags_path}: {summary['flag'].isin(['Caution', 'Discount']).sum()} rows")


if __name__ == "__main__":
    main()
