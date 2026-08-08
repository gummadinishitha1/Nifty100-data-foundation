"""Cash flow KPI formulas, capital allocation classification, and reports."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from math import isfinite
import re

import pandas as pd

from src.analytics.cagr import calculate_cagr, fiscal_year_sort_key


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
CASHFLOW_INTELLIGENCE_XLSX = OUTPUT_DIR / "cashflow_intelligence.xlsx"
DISTRESS_ALERTS_CSV = OUTPUT_DIR / "distress_alerts.csv"
CAPITAL_ALLOCATION_CSV = OUTPUT_DIR / "capital_allocation.csv"
PATTERN_DISTRIBUTION_CSV = OUTPUT_DIR / "capital_allocation_distribution.csv"
PATTERN_CHANGES_CSV = OUTPUT_DIR / "pattern_changes.csv"


def _num(value: float | int | None) -> float | None:
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(value):
        return None
    return value


def free_cash_flow(
    operating_activity: float | int | None,
    investing_activity: float | int | None,
) -> float | None:
    cfo = _num(operating_activity)
    cfi = _num(investing_activity)
    if cfo is None and cfi is None:
        return None
    return (cfo or 0.0) + (cfi or 0.0)


def cfo_quality_ratio(
    operating_activity: float | int | None,
    net_profit: float | int | None,
) -> float | None:
    pat = _num(net_profit)
    if pat in (None, 0):
        return None
    return (_num(operating_activity) or 0.0) / pat


def cfo_quality_label(average_ratio: float | None) -> str | None:
    if average_ratio is None:
        return None
    if average_ratio > 1.0:
        return "High Quality"
    if average_ratio >= 0.5:
        return "Moderate"
    return "Accrual Risk"


def capex_intensity(
    investing_activity: float | int | None,
    sales: float | int | None,
) -> float | None:
    sales_value = _num(sales)
    if sales_value in (None, 0):
        return None
    return abs(_num(investing_activity) or 0.0) / sales_value * 100


def capex_label(capex_intensity_pct: float | None) -> str | None:
    if capex_intensity_pct is None:
        return None
    if capex_intensity_pct < 3:
        return "Asset Light"
    if capex_intensity_pct <= 8:
        return "Moderate"
    return "Capital Intensive"


def fcf_conversion_rate(
    fcf: float | int | None,
    operating_profit: float | int | None,
) -> float | None:
    op = _num(operating_profit)
    if op in (None, 0):
        return None
    return (_num(fcf) or 0.0) / op * 100


def sign(value: float | int | None) -> str:
    value = _num(value) or 0.0
    return "+" if value >= 0 else "-"


def capital_allocation_pattern(
    operating_activity: float | int | None,
    investing_activity: float | int | None,
    financing_activity: float | int | None,
    cfo_pat_ratio: float | None = None,
) -> str:
    signs = (
        sign(operating_activity),
        sign(investing_activity),
        sign(financing_activity),
    )
    if signs == ("+", "-", "-") and cfo_pat_ratio is not None and cfo_pat_ratio > 1.0:
        return "Shareholder Returns"
    labels = {
        ("+", "-", "-"): "Reinvestor",
        ("+", "+", "-"): "Liquidating Assets",
        ("-", "+", "+"): "Distress Signal",
        ("-", "-", "+"): "Growth Funded by Debt",
        ("+", "+", "+"): "Cash Accumulator",
        ("-", "-", "-"): "Pre-Revenue",
        ("+", "-", "+"): "Mixed",
    }
    return labels.get(signs, "Mixed")


def distress_signal(operating_activity: float | int | None, financing_activity: float | int | None) -> bool:
    cfo = _num(operating_activity)
    cff = _num(financing_activity)
    return cfo is not None and cff is not None and cfo < 0 and cff > 0


def deleveraging_signal(
    financing_activity: float | int | None,
    latest_borrowings: float | int | None,
    previous_borrowings: float | int | None,
) -> bool:
    cff = _num(financing_activity)
    latest = _num(latest_borrowings)
    previous = _num(previous_borrowings)
    return cff is not None and cff < 0 and latest is not None and previous is not None and latest < previous


def _round(value: float | None, places: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), places)


def _fiscal_year_number(year_label: object) -> int | None:
    label = "" if year_label is None else str(year_label).strip()
    if not label or label.lower() == "ttm":
        return None
    four_digit = re.search(r"(\d{4})", label)
    if four_digit:
        return int(four_digit.group(1))
    two_digit = re.search(r"(\d{2})$", label)
    if two_digit:
        year = int(two_digit.group(1))
        return 2000 + year if year < 50 else 1900 + year
    return None


def _cashflow_year_sort_key(year_label: object) -> tuple[int, int, str]:
    label = "" if year_label is None else str(year_label)
    if label.strip().lower() == "ttm":
        return (9999, 12, label)
    parsed = _fiscal_year_number(label)
    if parsed is None:
        return fiscal_year_sort_key(label)
    month_order = {
        "JAN": 1,
        "FEB": 2,
        "MAR": 3,
        "APR": 4,
        "MAY": 5,
        "JUN": 6,
        "JUL": 7,
        "AUG": 8,
        "SEP": 9,
        "OCT": 10,
        "NOV": 11,
        "DEC": 12,
    }
    return (parsed, month_order.get(label[:3].upper(), 0), label)


def _non_ttm(df: pd.DataFrame) -> pd.DataFrame:
    if "year" not in df:
        return df.copy()
    return df[df["year"].astype(str).str.lower().ne("ttm")].copy()


def _load_cashflow_base(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        WITH cashflow_years AS (
            SELECT
                cf.*,
                CASE
                    WHEN substr(CAST(cf.year AS TEXT), -4) GLOB '[0-9][0-9][0-9][0-9]' THEN CAST(substr(CAST(cf.year AS TEXT), -4) AS INTEGER)
                    WHEN substr(CAST(cf.year AS TEXT), -2) GLOB '[0-9][0-9]' THEN 2000 + CAST(substr(CAST(cf.year AS TEXT), -2) AS INTEGER)
                    ELSE NULL
                END AS fiscal_year
            FROM cashflow cf
        ),
        pl_years AS (
            SELECT
                pl.*,
                CASE
                    WHEN substr(CAST(pl.year AS TEXT), -4) GLOB '[0-9][0-9][0-9][0-9]' THEN CAST(substr(CAST(pl.year AS TEXT), -4) AS INTEGER)
                    WHEN substr(CAST(pl.year AS TEXT), -2) GLOB '[0-9][0-9]' THEN 2000 + CAST(substr(CAST(pl.year AS TEXT), -2) AS INTEGER)
                    ELSE NULL
                END AS fiscal_year
            FROM profitandloss pl
        ),
        bs_years AS (
            SELECT
                bs.*,
                CASE
                    WHEN substr(CAST(bs.year AS TEXT), -4) GLOB '[0-9][0-9][0-9][0-9]' THEN CAST(substr(CAST(bs.year AS TEXT), -4) AS INTEGER)
                    WHEN substr(CAST(bs.year AS TEXT), -2) GLOB '[0-9][0-9]' THEN 2000 + CAST(substr(CAST(bs.year AS TEXT), -2) AS INTEGER)
                    ELSE NULL
                END AS fiscal_year
            FROM balancesheet bs
        )
        SELECT
            c.id AS company_id,
            s.broad_sector AS sector,
            cf.year,
            cf.operating_activity,
            cf.investing_activity,
            cf.financing_activity,
            pl.sales,
            pl.operating_profit,
            pl.net_profit,
            bs.borrowings
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN cashflow cf
            ON cf.company_id = c.id
        LEFT JOIN cashflow_years cfy
            ON cfy.company_id = c.id
           AND cfy.year = cf.year
        LEFT JOIN pl_years pl
            ON pl.company_id = c.id
           AND pl.fiscal_year = cfy.fiscal_year
        LEFT JOIN bs_years bs
            ON bs.company_id = c.id
           AND bs.fiscal_year = cfy.fiscal_year
        ORDER BY c.id, cf.year
        """,
        conn,
    )


def _load_capital_allocation(path: Path = CAPITAL_ALLOCATION_CSV) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["company_id", "year", "cfo_sign", "cfi_sign", "cff_sign", "pattern_label"])
    return pd.read_csv(path)


def _latest_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    df = _non_ttm(df)
    frames = []
    for _, group in df.groupby("company_id", sort=True):
        frames.append(group.sort_values("year", key=lambda values: values.map(_cashflow_year_sort_key)).tail(1))
    return pd.concat(frames, ignore_index=True) if frames else df.copy()


def build_cashflow_intelligence(base: pd.DataFrame, capital_allocation: pd.DataFrame | None = None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    capital_allocation = capital_allocation if capital_allocation is not None else pd.DataFrame()
    latest_patterns = _latest_rows(capital_allocation).set_index("company_id") if not capital_allocation.empty else pd.DataFrame()

    for company_id, group in base.groupby("company_id", sort=True):
        history = _non_ttm(group.dropna(subset=["year"])).sort_values("year", key=lambda values: values.map(_cashflow_year_sort_key)).copy()
        sector = group["sector"].dropna().iloc[-1] if group["sector"].notna().any() else None
        if history.empty:
            rows.append(
                {
                    "company_id": company_id,
                    "sector": sector,
                    "cfo_quality_score": None,
                    "cfo_quality_label": None,
                    "capex_intensity_pct": None,
                    "capex_label": None,
                    "fcf_cagr_5yr": None,
                    "fcf_conversion_pct": None,
                    "distress_flag": False,
                    "deleveraging_flag": False,
                    "capital_allocation_label": None,
                }
            )
            continue

        ratios = [cfo_quality_ratio(row.operating_activity, row.net_profit) for row in history.itertuples(index=False)]
        latest_quality_values = [value for value in ratios[-5:] if value is not None]
        cfo_quality_score = sum(latest_quality_values) / len(latest_quality_values) if latest_quality_values else None

        latest = history.iloc[-1]
        previous = history.iloc[-2] if len(history) >= 2 else None
        fcf_values = [free_cash_flow(row.operating_activity, row.investing_activity) for row in history.itertuples(index=False)]
        fcf_cagr = calculate_cagr(fcf_values[-6], fcf_values[-1], 5).value if len(fcf_values) >= 6 else None
        latest_fcf = fcf_values[-1]
        latest_capex = capex_intensity(latest.get("investing_activity"), latest.get("sales"))
        fcf_conversion = fcf_conversion_rate(latest_fcf, latest.get("operating_profit"))
        latest_pattern = (
            latest_patterns.loc[company_id, "pattern_label"]
            if not latest_patterns.empty and company_id in latest_patterns.index
            else capital_allocation_pattern(
                latest.get("operating_activity"),
                latest.get("investing_activity"),
                latest.get("financing_activity"),
                ratios[-1] if ratios else None,
            )
        )

        rows.append(
            {
                "company_id": company_id,
                "sector": sector,
                "cfo_quality_score": _round(cfo_quality_score),
                "cfo_quality_label": cfo_quality_label(cfo_quality_score),
                "capex_intensity_pct": _round(latest_capex),
                "capex_label": capex_label(latest_capex),
                "fcf_cagr_5yr": _round(fcf_cagr),
                "fcf_conversion_pct": _round(fcf_conversion),
                "distress_flag": distress_signal(latest.get("operating_activity"), latest.get("financing_activity")),
                "deleveraging_flag": deleveraging_signal(
                    latest.get("financing_activity"),
                    latest.get("borrowings"),
                    previous.get("borrowings") if previous is not None else None,
                ),
                "capital_allocation_label": latest_pattern,
            }
        )

    columns = [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]
    return pd.DataFrame(rows, columns=columns)


def build_distress_alerts(base: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for company_id, group in base.groupby("company_id", sort=True):
        history = _non_ttm(group.dropna(subset=["year"])).sort_values("year", key=lambda values: values.map(_cashflow_year_sort_key))
        if history.empty:
            continue
        latest = history.iloc[-1]
        if distress_signal(latest.get("operating_activity"), latest.get("financing_activity")):
            rows.append(
                {
                    "company_id": company_id,
                    "year": latest.get("year"),
                    "cfo_value": latest.get("operating_activity"),
                    "cff_value": latest.get("financing_activity"),
                    "latest_net_profit": latest.get("net_profit"),
                }
            )
    return pd.DataFrame(rows, columns=["company_id", "year", "cfo_value", "cff_value", "latest_net_profit"])


def verify_capital_allocation_complete(conn: sqlite3.Connection, capital_allocation: pd.DataFrame) -> pd.DataFrame:
    expected = pd.read_sql_query(
        """
        SELECT cf.company_id, cf.year
        FROM cashflow cf
        INNER JOIN sectors s
            ON s.company_id = cf.company_id
        WHERE lower(CAST(cf.year AS TEXT)) <> 'ttm'
        """,
        conn,
    )
    expected["fiscal_year"] = expected["year"].map(_fiscal_year_number)
    actual = capital_allocation[["company_id", "year"]].drop_duplicates() if not capital_allocation.empty else pd.DataFrame(columns=["company_id", "year"])
    actual = _non_ttm(actual)
    actual["fiscal_year"] = actual["year"].map(_fiscal_year_number)
    actual_keys = actual[["company_id", "fiscal_year"]].dropna().drop_duplicates()
    return (
        expected.merge(actual_keys, on=["company_id", "fiscal_year"], how="left", indicator=True)
        .query("_merge == 'left_only'")
        .drop(columns=["_merge", "fiscal_year"])
    )


def build_latest_pattern_distribution(capital_allocation: pd.DataFrame) -> pd.DataFrame:
    latest = _latest_rows(capital_allocation)
    return (
        latest["pattern_label"]
        .value_counts()
        .rename_axis("pattern_label")
        .reset_index(name="company_count")
        .sort_values(["company_count", "pattern_label"], ascending=[False, True])
        .reset_index(drop=True)
    )


def build_pattern_changes(capital_allocation: pd.DataFrame, sectors: pd.DataFrame | None = None) -> pd.DataFrame:
    rows = []
    sector_map = {}
    if sectors is not None and not sectors.empty:
        sector_map = sectors.dropna(subset=["company_id"]).set_index("company_id")["broad_sector"].to_dict()

    for company_id, group in capital_allocation.groupby("company_id", sort=True):
        history = _non_ttm(group).sort_values("year", key=lambda values: values.map(_cashflow_year_sort_key))
        if len(history) < 2:
            continue
        previous = history.iloc[-2]
        latest = history.iloc[-1]
        if previous["pattern_label"] != latest["pattern_label"]:
            rows.append(
                {
                    "company_id": company_id,
                    "sector": sector_map.get(company_id),
                    "previous_year": previous["year"],
                    "latest_year": latest["year"],
                    "previous_pattern": previous["pattern_label"],
                    "latest_pattern": latest["pattern_label"],
                    "change_text": f"{company_id} moved from {previous['pattern_label']} to {latest['pattern_label']}",
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "company_id",
            "sector",
            "previous_year",
            "latest_year",
            "previous_pattern",
            "latest_pattern",
            "change_text",
        ],
    )


def generate_cashflow_intelligence(db_path: Path = DB_PATH, output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    output_dir.mkdir(exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        base = _load_cashflow_base(conn)
        capital_allocation = _load_capital_allocation(output_dir / CAPITAL_ALLOCATION_CSV.name)
        sectors = pd.read_sql_query("SELECT company_id, broad_sector FROM sectors", conn)
        sector_universe = set(sectors["company_id"].dropna().astype(str))
        base = base[base["company_id"].astype(str).isin(sector_universe)].copy()
        missing_capital_allocation = verify_capital_allocation_complete(conn, capital_allocation)

    intelligence = build_cashflow_intelligence(base, capital_allocation)
    distress_alerts = build_distress_alerts(base)
    distribution = build_latest_pattern_distribution(capital_allocation)
    pattern_changes = build_pattern_changes(capital_allocation, sectors)

    intelligence.to_excel(output_dir / CASHFLOW_INTELLIGENCE_XLSX.name, index=False)
    distress_alerts.to_csv(output_dir / DISTRESS_ALERTS_CSV.name, index=False)
    distribution.to_csv(output_dir / PATTERN_DISTRIBUTION_CSV.name, index=False)
    pattern_changes.to_csv(output_dir / PATTERN_CHANGES_CSV.name, index=False)

    return {
        "cashflow_intelligence": intelligence,
        "distress_alerts": distress_alerts,
        "pattern_distribution": distribution,
        "pattern_changes": pattern_changes,
        "missing_capital_allocation": missing_capital_allocation,
    }


def main() -> None:
    outputs = generate_cashflow_intelligence()
    print(f"Wrote {CASHFLOW_INTELLIGENCE_XLSX}: {len(outputs['cashflow_intelligence'])} companies")
    print(f"Wrote {DISTRESS_ALERTS_CSV}: {len(outputs['distress_alerts'])} alerts")
    print(f"Wrote {PATTERN_DISTRIBUTION_CSV}: {len(outputs['pattern_distribution'])} pattern rows")
    print(f"Wrote {PATTERN_CHANGES_CSV}: {len(outputs['pattern_changes'])} changes")
    print(f"Capital allocation missing rows for sector universe: {len(outputs['missing_capital_allocation'])}")


if __name__ == "__main__":
    main()
