"""Populate the computed financial_ratios table and Sprint 2 outputs."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd

from src.analytics.cagr import fiscal_year_sort_key, windowed_cagr
from src.analytics.cashflow_kpis import (
    capex_intensity,
    capex_label,
    capital_allocation_pattern,
    cfo_quality_label,
    cfo_quality_ratio,
    fcf_conversion_rate,
    free_cash_flow,
    sign,
)
from src.analytics.ratios import (
    asset_turnover,
    book_value_per_share,
    debt_to_equity,
    dividend_payout_ratio,
    earnings_per_share,
    high_leverage_flag,
    interest_coverage_ratio,
    net_debt,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
EDGE_LOG = OUTPUT_DIR / "ratio_edge_cases.log"
CAPITAL_ALLOCATION_CSV = OUTPUT_DIR / "capital_allocation.csv"


def _round(value: float | None, places: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), places)


def _source_category(diff: float, metric: str) -> str:
    if metric == "ROE" and diff > 50:
        return "data source issue"
    if diff <= 10:
        return "version difference"
    return "formula discrepancy"


def _ensure_computed_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(financial_ratios)")}
    additions = {
        "net_profit_margin_pct": "REAL",
        "operating_profit_margin_pct": "REAL",
        "opm_source_difference_pct": "REAL",
        "opm_mismatch_flag": "INTEGER DEFAULT 0",
        "return_on_equity_pct": "REAL",
        "return_on_capital_employed_pct": "REAL",
        "roce_benchmark_type": "TEXT",
        "return_on_assets_pct": "REAL",
        "high_leverage_flag": "INTEGER DEFAULT 0",
        "icr_label": "TEXT",
        "icr_warning_flag": "INTEGER DEFAULT 0",
        "net_debt_cr": "REAL",
        "asset_turnover": "REAL",
        "free_cash_flow_cr": "REAL",
        "capex_cr": "REAL",
        "capex_intensity_label": "TEXT",
        "fcf_conversion_rate_pct": "REAL",
        "cfo_quality_5yr": "REAL",
        "cfo_quality_label": "TEXT",
        "earnings_per_share": "REAL",
        "book_value_per_share": "REAL",
        "dividend_payout_ratio_pct": "REAL",
        "total_debt_cr": "REAL",
        "cash_from_operations_cr": "REAL",
        "revenue_cagr_3yr": "REAL",
        "revenue_cagr_3yr_flag": "TEXT",
        "revenue_cagr_5yr": "REAL",
        "revenue_cagr_5yr_flag": "TEXT",
        "revenue_cagr_10yr": "REAL",
        "revenue_cagr_10yr_flag": "TEXT",
        "pat_cagr_3yr": "REAL",
        "pat_cagr_3yr_flag": "TEXT",
        "pat_cagr_5yr": "REAL",
        "pat_cagr_5yr_flag": "TEXT",
        "pat_cagr_10yr": "REAL",
        "pat_cagr_10yr_flag": "TEXT",
        "eps_cagr_3yr": "REAL",
        "eps_cagr_3yr_flag": "TEXT",
        "eps_cagr_5yr": "REAL",
        "eps_cagr_5yr_flag": "TEXT",
        "eps_cagr_10yr": "REAL",
        "eps_cagr_10yr_flag": "TEXT",
        "composite_quality_score": "REAL",
    }
    for column, definition in additions.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE financial_ratios ADD COLUMN {column} {definition}")


def _load_base(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql_query(
        """
        SELECT
            p.company_id,
            p.year,
            p.sales,
            p.operating_profit,
            p.opm_percentage,
            p.other_income,
            p.interest,
            p.depreciation,
            p.net_profit,
            p.eps,
            p.dividend_payout,
            b.equity_capital,
            b.reserves,
            b.borrowings,
            b.investments,
            b.total_assets,
            cf.operating_activity,
            cf.investing_activity,
            cf.financing_activity,
            s.broad_sector,
            c.face_value,
            c.roce_percentage AS source_roce_percentage,
            c.roe_percentage AS source_roe_percentage,
            mc.pe_ratio,
            mc.pb_ratio,
            mc.dividend_yield_pct
        FROM profitandloss p
        LEFT JOIN balancesheet b
            ON b.company_id = p.company_id
           AND b.year = p.year
        LEFT JOIN cashflow cf
            ON cf.company_id = p.company_id
           AND cf.year = p.year
        LEFT JOIN sectors s
            ON s.company_id = p.company_id
        LEFT JOIN companies c
            ON c.id = p.company_id
        LEFT JOIN market_cap mc
            ON mc.company_id = p.company_id
           AND mc.year = p.year
        ORDER BY p.company_id, p.year
        """,
        conn,
    )


def _add_window_metrics(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in df.groupby("company_id", sort=False):
        group = group.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key)).copy()
        for metric, source in [
            ("revenue", "sales"),
            ("pat", "net_profit"),
            ("eps", "eps"),
        ]:
            values = group[source].tolist()
            for years in (3, 5, 10):
                cagr_values = []
                flags = []
                for idx in range(len(group)):
                    result = windowed_cagr(values, idx, years)
                    cagr_values.append(result.value)
                    flags.append(result.flag)
                group[f"{metric}_cagr_{years}yr"] = cagr_values
                group[f"{metric}_cagr_{years}yr_flag"] = flags
        frames.append(group)
    return pd.concat(frames, ignore_index=True)


def _add_cfo_quality(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for _, group in df.groupby("company_id", sort=False):
        group = group.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key)).copy()
        ratios = [
            cfo_quality_ratio(row.operating_activity, row.net_profit)
            for row in group.itertuples(index=False)
        ]
        averages = []
        labels = []
        for idx in range(len(ratios)):
            window = [value for value in ratios[max(0, idx - 4) : idx + 1] if value is not None]
            average = sum(window) / len(window) if window else None
            averages.append(average)
            labels.append(cfo_quality_label(average))
        group["cfo_quality_5yr"] = averages
        group["cfo_quality_label"] = labels
        frames.append(group)
    return pd.concat(frames, ignore_index=True)


def build_ratios(conn: sqlite3.Connection) -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
    df = _load_base(conn)
    df = _add_window_metrics(df)
    df = _add_cfo_quality(df)

    rows = []
    capital_rows = []
    edge_lines = []

    for row in df.itertuples(index=False):
        opm = operating_profit_margin(row.operating_profit, row.sales, row.opm_percentage)
        roe_value = return_on_equity(row.net_profit, row.equity_capital, row.reserves)
        ebit = (row.operating_profit or 0) + (row.other_income or 0)
        roce_value = return_on_capital_employed(
            ebit,
            row.equity_capital,
            row.reserves,
            row.borrowings,
        )
        de_value = debt_to_equity(row.borrowings, row.equity_capital, row.reserves)
        icr = interest_coverage_ratio(row.operating_profit, row.other_income, row.interest)
        fcf = free_cash_flow(row.operating_activity, row.investing_activity)
        capex = capex_intensity(row.investing_activity, row.sales)
        fcf_conversion = fcf_conversion_rate(fcf, row.operating_profit)
        cfo_pat = cfo_quality_ratio(row.operating_activity, row.net_profit)
        pattern = capital_allocation_pattern(
            row.operating_activity,
            row.investing_activity,
            row.financing_activity,
            cfo_pat,
        )

        if opm.mismatch:
            edge_lines.append(
                f"{row.company_id},{row.year},OPM,{opm.value:.4f},{row.opm_percentage},formula discrepancy,"
                f"computed OPM differs from source by {opm.source_difference_pct:.4f} percentage points"
            )
        if roce_value is not None and row.source_roce_percentage is not None:
            diff = abs(roce_value - float(row.source_roce_percentage))
            if diff > 5:
                category = _source_category(diff, "ROCE")
                edge_lines.append(
                    f"{row.company_id},{row.year},ROCE,{roce_value:.4f},{row.source_roce_percentage},{category},"
                    f"computed ROCE differs from company-level source display value by {diff:.4f} percentage points"
                )
        if roe_value is not None and row.source_roe_percentage is not None:
            diff = abs(roe_value - float(row.source_roe_percentage))
            if diff > 5:
                category = _source_category(diff, "ROE")
                edge_lines.append(
                    f"{row.company_id},{row.year},ROE,{roe_value:.4f},{row.source_roe_percentage},{category},"
                    f"computed ROE retained for analytics; source value retained only for display"
                )

        quality_inputs = [
            roe_value,
            roce_value,
            row.cfo_quality_5yr * 100 if row.cfo_quality_5yr is not None else None,
            fcf_conversion,
        ]
        quality_values = [value for value in quality_inputs if value is not None]
        composite = sum(quality_values) / len(quality_values) if quality_values else None

        rows.append(
            {
                "id": f"{row.company_id}_{row.year}".replace(" ", "_"),
                "company_id": row.company_id,
                "year": row.year,
                "pe_ratio": row.pe_ratio,
                "pb_ratio": row.pb_ratio,
                "dividend_yield": row.dividend_yield_pct,
                "roe": _round(roe_value),
                "roce": _round(roce_value),
                "debt_to_equity": _round(de_value),
                "interest_coverage": _round(icr.value),
                "sales_growth": _round(row.revenue_cagr_3yr),
                "profit_growth": _round(row.pat_cagr_3yr),
                "eps_growth": _round(row.eps_cagr_3yr),
                "opm": _round(opm.value),
                "npm": _round(net_profit_margin(row.net_profit, row.sales)),
                "other_ratio": None,
                "net_profit_margin_pct": _round(net_profit_margin(row.net_profit, row.sales)),
                "operating_profit_margin_pct": _round(opm.value),
                "opm_source_difference_pct": _round(opm.source_difference_pct),
                "opm_mismatch_flag": int(opm.mismatch),
                "return_on_equity_pct": _round(roe_value),
                "return_on_capital_employed_pct": _round(roce_value),
                "roce_benchmark_type": "sector_relative" if row.broad_sector == "Financials" else "absolute",
                "return_on_assets_pct": _round(return_on_assets(row.net_profit, row.total_assets)),
                "high_leverage_flag": int(high_leverage_flag(de_value, row.broad_sector)),
                "icr_label": icr.label,
                "icr_warning_flag": int(icr.warning_flag),
                "net_debt_cr": _round(net_debt(row.borrowings, row.investments)),
                "asset_turnover": _round(asset_turnover(row.sales, row.total_assets)),
                "free_cash_flow_cr": _round(fcf),
                "capex_cr": _round(abs(row.investing_activity) if row.investing_activity is not None else None),
                "capex_intensity_label": capex_label(capex),
                "fcf_conversion_rate_pct": _round(fcf_conversion),
                "cfo_quality_5yr": _round(row.cfo_quality_5yr),
                "cfo_quality_label": row.cfo_quality_label,
                "earnings_per_share": _round(row.eps if row.eps is not None else earnings_per_share(row.net_profit, row.equity_capital)),
                "book_value_per_share": _round(book_value_per_share(row.equity_capital, row.reserves, row.face_value)),
                "dividend_payout_ratio_pct": _round(dividend_payout_ratio(row.dividend_payout)),
                "total_debt_cr": _round(row.borrowings),
                "cash_from_operations_cr": _round(row.operating_activity),
                "revenue_cagr_3yr": _round(row.revenue_cagr_3yr),
                "revenue_cagr_3yr_flag": row.revenue_cagr_3yr_flag,
                "revenue_cagr_5yr": _round(row.revenue_cagr_5yr),
                "revenue_cagr_5yr_flag": row.revenue_cagr_5yr_flag,
                "revenue_cagr_10yr": _round(row.revenue_cagr_10yr),
                "revenue_cagr_10yr_flag": row.revenue_cagr_10yr_flag,
                "pat_cagr_3yr": _round(row.pat_cagr_3yr),
                "pat_cagr_3yr_flag": row.pat_cagr_3yr_flag,
                "pat_cagr_5yr": _round(row.pat_cagr_5yr),
                "pat_cagr_5yr_flag": row.pat_cagr_5yr_flag,
                "pat_cagr_10yr": _round(row.pat_cagr_10yr),
                "pat_cagr_10yr_flag": row.pat_cagr_10yr_flag,
                "eps_cagr_3yr": _round(row.eps_cagr_3yr),
                "eps_cagr_3yr_flag": row.eps_cagr_3yr_flag,
                "eps_cagr_5yr": _round(row.eps_cagr_5yr),
                "eps_cagr_5yr_flag": row.eps_cagr_5yr_flag,
                "eps_cagr_10yr": _round(row.eps_cagr_10yr),
                "eps_cagr_10yr_flag": row.eps_cagr_10yr_flag,
                "composite_quality_score": _round(composite),
            }
        )
        capital_rows.append(
            {
                "company_id": row.company_id,
                "year": row.year,
                "cfo_sign": sign(row.operating_activity),
                "cfi_sign": sign(row.investing_activity),
                "cff_sign": sign(row.financing_activity),
                "pattern_label": pattern,
            }
        )

    return pd.DataFrame(rows), edge_lines, pd.DataFrame(capital_rows)


def populate_financial_ratios(db_path: Path = DB_PATH) -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _ensure_computed_columns(conn)
        ratios, edge_lines, capital_allocation = build_ratios(conn)
        conn.execute("DELETE FROM financial_ratios")
        ratios.to_sql("financial_ratios", conn, if_exists="append", index=False)
        conn.commit()

    capital_allocation.to_csv(CAPITAL_ALLOCATION_CSV, index=False)
    header = "company_id,year,metric,computed_value,source_value,category,explanation"
    EDGE_LOG.write_text(header + "\n" + "\n".join(edge_lines) + "\n", encoding="utf-8")
    return len(ratios)


if __name__ == "__main__":
    count = populate_financial_ratios()
    print(f"Populated financial_ratios: {count} rows")
    print(f"Wrote {CAPITAL_ALLOCATION_CSV}")
    print(f"Wrote {EDGE_LOG}")
