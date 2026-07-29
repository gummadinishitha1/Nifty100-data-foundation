"""Cached SQLite data loaders for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path
import sqlite3

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[3]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    return sqlite3.connect(DB_PATH)


def _read_sql(query: str, params: tuple[object, ...] = ()) -> pd.DataFrame:
    with _connect() as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data(ttl=600)
def get_companies() -> pd.DataFrame:
    """Return the company master list with sector metadata."""
    return _read_sql(
        """
        SELECT
            c.id AS ticker,
            c.company_name,
            c.about_company,
            c.website,
            c.face_value,
            c.book_value,
            c.roce_percentage,
            c.roe_percentage,
            s.broad_sector,
            s.sub_sector,
            s.index_weight_pct,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        ORDER BY c.id
        """
    )


@st.cache_data(ttl=600)
def get_ratios(ticker: str, year: str | int | None = None) -> pd.DataFrame:
    """Return financial ratio rows for one company, optionally filtered by year."""
    params: list[object] = [ticker]
    year_clause = ""
    if year is not None:
        year_clause = "AND CAST(fr.year AS TEXT) = CAST(? AS TEXT)"
        params.append(year)

    return _read_sql(
        f"""
        SELECT fr.*
        FROM financial_ratios fr
        WHERE fr.company_id = ?
        {year_clause}
        ORDER BY
            CASE WHEN lower(CAST(fr.year AS TEXT)) = 'ttm' THEN 9999
                 ELSE CAST(fr.year AS INTEGER)
            END
        """,
        tuple(params),
    )


@st.cache_data(ttl=600)
def get_pl(ticker: str) -> pd.DataFrame:
    """Return profit and loss rows for one company."""
    return _read_sql(
        """
        SELECT *
        FROM profitandloss
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_bs(ticker: str) -> pd.DataFrame:
    """Return balance sheet rows for one company."""
    return _read_sql(
        """
        SELECT *
        FROM balancesheet
        WHERE company_id = ?
        ORDER BY year
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_cf(ticker: str) -> pd.DataFrame:
    """Return cash flow rows for one company."""
    return _read_sql(
        """
        SELECT *
        FROM cashflow
        WHERE company_id = ?
        ORDER BY
            CASE WHEN lower(CAST(year AS TEXT)) = 'ttm' THEN 9999
                 ELSE CAST(year AS INTEGER)
            END
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_sectors() -> pd.DataFrame:
    """Return sector-level company counts and index weights."""
    return _read_sql(
        """
        SELECT
            COALESCE(s.broad_sector, 'Unassigned') AS broad_sector,
            COUNT(DISTINCT c.id) AS company_count,
            ROUND(SUM(COALESCE(s.index_weight_pct, 0)), 2) AS index_weight_pct,
            ROUND(AVG(c.roe_percentage), 2) AS avg_roe_pct,
            ROUND(AVG(c.roce_percentage), 2) AS avg_roce_pct
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        GROUP BY COALESCE(s.broad_sector, 'Unassigned')
        ORDER BY index_weight_pct DESC, company_count DESC
        """
    )


@st.cache_data(ttl=600)
def get_yearly_universe(year: int) -> pd.DataFrame:
    """Return company metrics for rows matching one fiscal/calendar year."""
    return _read_sql(
        """
        SELECT
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            fr.year,
            fr.pe_ratio,
            fr.pb_ratio,
            fr.dividend_yield,
            fr.debt_to_equity,
            fr.interest_coverage,
            COALESCE(fr.return_on_equity_pct, fr.roe) AS return_on_equity_pct,
            COALESCE(fr.return_on_capital_employed_pct, fr.roce) AS return_on_capital_employed_pct,
            COALESCE(fr.operating_profit_margin_pct, fr.opm) AS operating_profit_margin_pct,
            COALESCE(fr.net_profit_margin_pct, fr.npm) AS net_profit_margin_pct,
            fr.free_cash_flow_cr,
            fr.revenue_cagr_5yr,
            fr.pat_cagr_5yr,
            fr.composite_quality_score
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN financial_ratios fr
            ON fr.company_id = c.id
           AND CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) = ?
           AND lower(CAST(fr.year AS TEXT)) <> 'ttm'
        ORDER BY fr.composite_quality_score DESC, c.id
        """,
        (year,),
    )


@st.cache_data(ttl=600)
def get_company_profile(ticker: str) -> pd.DataFrame:
    """Return one company profile row with sector metadata."""
    return _read_sql(
        """
        SELECT
            c.id AS ticker,
            c.company_name,
            c.about_company,
            c.website,
            c.nse_profile,
            c.bse_profile,
            s.broad_sector,
            s.sub_sector,
            s.market_cap_category
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        WHERE upper(c.id) = upper(?)
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_company_pros_cons(ticker: str) -> pd.DataFrame:
    """Return pros and cons for one company."""
    return _read_sql(
        """
        SELECT pros, cons
        FROM prosandcons
        WHERE upper(company_id) = upper(?)
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_trend_metrics(ticker: str) -> pd.DataFrame:
    """Return a 10-year trend table combining P&L, ratios, cash flow, and market cap."""
    return _read_sql(
        """
        WITH yearly_ratios AS (
            SELECT *
            FROM (
                SELECT
                    fr.*,
                    CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) AS fiscal_year,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id, CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER)
                        ORDER BY fr.rowid DESC
                    ) AS row_number
                FROM financial_ratios fr
                WHERE lower(CAST(fr.year AS TEXT)) <> 'ttm'
            )
            WHERE row_number = 1
        )
        SELECT *
        FROM (
            SELECT
                pl.year,
                pl.sales AS revenue,
                pl.net_profit,
                yr.return_on_equity_pct AS roe,
                yr.return_on_capital_employed_pct AS roce,
                yr.debt_to_equity,
                yr.pe_ratio,
                yr.pb_ratio,
                yr.operating_profit_margin_pct AS opm,
                yr.net_profit_margin_pct AS npm,
                yr.free_cash_flow_cr AS fcf,
                yr.revenue_cagr_5yr,
                yr.pat_cagr_5yr,
                cf.operating_activity AS cfo,
                cf.net_cash_flow,
                mc.market_cap_crore
            FROM profitandloss pl
            LEFT JOIN yearly_ratios yr
                ON yr.company_id = pl.company_id
               AND yr.fiscal_year = pl.year
            LEFT JOIN cashflow cf
                ON cf.company_id = pl.company_id
               AND CAST(substr(CAST(cf.year AS TEXT), -4) AS INTEGER) = pl.year
            LEFT JOIN market_cap mc
                ON mc.company_id = pl.company_id
               AND mc.year = pl.year
            WHERE upper(pl.company_id) = upper(?)
            ORDER BY pl.year DESC
            LIMIT 10
        )
        ORDER BY year
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_sector_company_metrics(sector: str, year: int = 2024) -> pd.DataFrame:
    """Return sector companies with revenue, ROE, market cap, and median KPI inputs."""
    return _read_sql(
        """
        WITH yearly_ratios AS (
            SELECT *
            FROM (
                SELECT
                    fr.*,
                    CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) AS fiscal_year,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id, CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER)
                        ORDER BY fr.rowid DESC
                    ) AS row_number
                FROM financial_ratios fr
                WHERE lower(CAST(fr.year AS TEXT)) <> 'ttm'
            )
            WHERE row_number = 1
        )
        SELECT
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            pl.sales AS revenue,
            pl.net_profit,
            yr.return_on_equity_pct AS roe,
            yr.return_on_capital_employed_pct AS roce,
            yr.debt_to_equity,
            yr.pe_ratio,
            yr.pb_ratio,
            yr.operating_profit_margin_pct AS opm,
            yr.net_profit_margin_pct AS npm,
            yr.revenue_cagr_5yr,
            yr.pat_cagr_5yr,
            mc.market_cap_crore
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN profitandloss pl
            ON pl.company_id = c.id
           AND pl.year = ?
        LEFT JOIN yearly_ratios yr
            ON yr.company_id = c.id
           AND yr.fiscal_year = ?
        LEFT JOIN market_cap mc
            ON mc.company_id = c.id
           AND mc.year = ?
        WHERE COALESCE(s.broad_sector, 'Unassigned') = ?
        ORDER BY mc.market_cap_crore DESC, c.id
        """,
        (year, year, year, sector),
    )


@st.cache_data(ttl=600)
def get_capital_allocation_map() -> pd.DataFrame:
    """Return latest company rows classified into capital allocation patterns."""
    return _read_sql(
        """
        WITH latest_ratios AS (
            SELECT *
            FROM (
                SELECT
                    fr.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id
                        ORDER BY CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) DESC, fr.rowid DESC
                    ) AS row_number
                FROM financial_ratios fr
                WHERE lower(CAST(fr.year AS TEXT)) <> 'ttm'
            )
            WHERE row_number = 1
        ),
        latest_market AS (
            SELECT mc.*
            FROM market_cap mc
            JOIN (
                SELECT company_id, MAX(year) AS latest_year
                FROM market_cap
                GROUP BY company_id
            ) latest
                ON latest.company_id = mc.company_id
               AND latest.latest_year = mc.year
        )
        SELECT
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            lr.return_on_equity_pct,
            lr.return_on_capital_employed_pct,
            lr.debt_to_equity,
            lr.free_cash_flow_cr,
            lr.revenue_cagr_5yr,
            lr.pat_cagr_5yr,
            lr.dividend_yield,
            COALESCE(lm.market_cap_crore, 1) AS market_cap_crore,
            CASE
                WHEN COALESCE(lr.debt_to_equity, 0) <= 0.10 AND COALESCE(lr.free_cash_flow_cr, 0) > 0 AND COALESCE(lr.revenue_cagr_5yr, 0) >= 10 THEN 'Debt-Free Compounders'
                WHEN COALESCE(lr.return_on_equity_pct, 0) >= 18 AND COALESCE(lr.revenue_cagr_5yr, 0) >= 10 THEN 'High ROE Reinvestors'
                WHEN COALESCE(lr.free_cash_flow_cr, 0) > 1000 AND COALESCE(lr.dividend_yield, 0) >= 1 THEN 'Cash Returners'
                WHEN COALESCE(lr.debt_to_equity, 0) > 1.5 AND COALESCE(lr.revenue_cagr_5yr, 0) >= 8 THEN 'Leveraged Growth'
                WHEN COALESCE(lr.pat_cagr_5yr, 0) < 0 AND COALESCE(lr.revenue_cagr_5yr, 0) > 0 THEN 'Turnaround Candidates'
                WHEN COALESCE(lr.pe_ratio, 999) <= 20 OR COALESCE(lr.pb_ratio, 999) <= 2 THEN 'Value Allocators'
                WHEN COALESCE(lr.capex_cr, 0) > COALESCE(lr.free_cash_flow_cr, 0) THEN 'Asset-Heavy Builders'
                ELSE 'Balanced Allocators'
            END AS allocation_pattern
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN latest_ratios lr
            ON lr.company_id = c.id
        LEFT JOIN latest_market lm
            ON lm.company_id = c.id
        ORDER BY allocation_pattern, c.id
        """
    )


@st.cache_data(ttl=600)
def get_annual_reports(ticker: str) -> pd.DataFrame:
    """Return annual report links for one company."""
    return _read_sql(
        """
        SELECT
            company_id AS ticker,
            Year AS year,
            Annual_Report AS annual_report_url
        FROM documents
        WHERE upper(company_id) = upper(?)
        ORDER BY Year DESC
        """,
        (ticker,),
    )


@st.cache_data(ttl=600)
def get_peers(group_name: str) -> pd.DataFrame:
    """Return companies and latest quality metrics in one peer group."""
    return _read_sql(
        """
        WITH latest_ratios AS (
            SELECT *
            FROM (
                SELECT
                    fr.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id
                        ORDER BY CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) DESC, fr.rowid DESC
                    ) AS row_number
                FROM financial_ratios fr
                WHERE lower(CAST(fr.year AS TEXT)) <> 'ttm'
            )
            WHERE row_number = 1
        )
        SELECT
            pg.peer_group_name,
            pg.is_benchmark,
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            lr.year,
            lr.composite_quality_score,
            lr.return_on_equity_pct,
            lr.return_on_capital_employed_pct,
            lr.debt_to_equity,
            lr.pe_ratio,
            lr.pb_ratio,
            lr.free_cash_flow_cr
        FROM peer_groups pg
        JOIN companies c
            ON c.id = pg.company_id
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN latest_ratios lr
            ON lr.company_id = c.id
        WHERE pg.peer_group_name = ?
        ORDER BY pg.is_benchmark DESC, c.id
        """,
        (group_name,),
    )


@st.cache_data(ttl=600)
def get_peer_groups() -> pd.DataFrame:
    """Return available peer group names."""
    return _read_sql(
        """
        SELECT peer_group_name, COUNT(*) AS company_count
        FROM peer_groups
        GROUP BY peer_group_name
        ORDER BY peer_group_name
        """
    )


@st.cache_data(ttl=600)
def get_screener_universe() -> pd.DataFrame:
    """Return latest company rows for dashboard screening and CSV export."""
    return _read_sql(
        """
        WITH latest_ratios AS (
            SELECT *
            FROM (
                SELECT
                    fr.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id
                        ORDER BY CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) DESC, fr.rowid DESC
                    ) AS row_number
                FROM financial_ratios fr
                WHERE lower(CAST(fr.year AS TEXT)) <> 'ttm'
            )
            WHERE row_number = 1
        )
        SELECT
            c.id AS ticker,
            c.company_name,
            s.broad_sector,
            s.sub_sector,
            lr.year,
            lr.composite_quality_score,
            lr.return_on_equity_pct,
            lr.return_on_capital_employed_pct,
            lr.net_profit_margin_pct,
            COALESCE(lr.operating_profit_margin_pct, lr.opm) AS operating_profit_margin_pct,
            lr.debt_to_equity,
            lr.interest_coverage,
            lr.pe_ratio,
            lr.pb_ratio,
            lr.dividend_yield,
            lr.free_cash_flow_cr,
            lr.revenue_cagr_5yr,
            lr.pat_cagr_5yr,
            lr.eps_cagr_5yr
        FROM companies c
        LEFT JOIN sectors s
            ON s.company_id = c.id
        LEFT JOIN latest_ratios lr
            ON lr.company_id = c.id
        ORDER BY lr.composite_quality_score DESC, c.id
        """
    )


@st.cache_data(ttl=600)
def get_valuation(ticker: str) -> pd.DataFrame:
    """Return a lightweight valuation view for one company."""
    return _read_sql(
        """
        WITH latest_ratios AS (
            SELECT *
            FROM (
                SELECT
                    fr.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY fr.company_id
                        ORDER BY CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) DESC, fr.rowid DESC
                    ) AS row_number
                FROM financial_ratios fr
                WHERE lower(CAST(fr.year AS TEXT)) <> 'ttm'
            )
            WHERE row_number = 1
        ),
        latest_market AS (
            SELECT mc.*
            FROM market_cap mc
            JOIN (
                SELECT company_id, MAX(year) AS latest_year
                FROM market_cap
                GROUP BY company_id
            ) latest
                ON latest.company_id = mc.company_id
               AND latest.latest_year = mc.year
        )
        SELECT
            c.id AS ticker,
            c.company_name,
            lr.year AS ratio_year,
            lm.year AS market_year,
            COALESCE(lm.market_cap_crore, 0) AS market_cap_crore,
            lr.free_cash_flow_cr,
            CASE
                WHEN lm.market_cap_crore IS NULL OR lm.market_cap_crore = 0 THEN NULL
                ELSE ROUND(lr.free_cash_flow_cr / lm.market_cap_crore * 100, 2)
            END AS fcf_yield_pct,
            COALESCE(lm.pe_ratio, lr.pe_ratio) AS pe_ratio,
            COALESCE(lm.pb_ratio, lr.pb_ratio) AS pb_ratio,
            CASE
                WHEN COALESCE(lm.pe_ratio, lr.pe_ratio) >= 60 THEN 'High P/E'
                WHEN COALESCE(lm.pe_ratio, lr.pe_ratio) <= 20 THEN 'Low P/E'
                ELSE 'Neutral P/E'
            END AS pe_flag,
            CASE
                WHEN lm.market_cap_crore IS NULL OR lm.market_cap_crore = 0 THEN 'Insufficient data'
                WHEN lr.free_cash_flow_cr / lm.market_cap_crore * 100 >= 5 THEN 'Discount'
                WHEN COALESCE(lm.pe_ratio, lr.pe_ratio) >= 60 THEN 'Overvalued'
                ELSE 'Fair'
            END AS valuation_label
        FROM companies c
        LEFT JOIN latest_ratios lr
            ON lr.company_id = c.id
        LEFT JOIN latest_market lm
            ON lm.company_id = c.id
        WHERE c.id = ?
        """,
        (ticker,),
    )
