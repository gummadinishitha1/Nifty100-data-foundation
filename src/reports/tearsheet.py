"""Generate company tearsheets, sector reports, and portfolio summary PDFs."""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.analytics.cagr import fiscal_year_sort_key


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = ROOT / "reports"
TEARSHEET_DIR = REPORTS_DIR / "tearsheets"
SECTOR_DIR = REPORTS_DIR / "sector"
PORTFOLIO_DIR = REPORTS_DIR / "portfolio"
SKIPPED_CSV = OUTPUT_DIR / "skipped_tearsheets.csv"
PROS_CONS_CANONICAL = OUTPUT_DIR / "pros_cons_generated.csv"

NAVY = colors.HexColor("#12233f")
GREEN = colors.HexColor("#238443")
RED = colors.HexColor("#b42318")
LIGHT_BG = colors.HexColor("#f4f7fb")
GRID = colors.HexColor("#d7deea")
TEXT = colors.HexColor("#1f2937")


@dataclass(frozen=True)
class ReportData:
    companies: pd.DataFrame
    pl: pd.DataFrame
    bs: pd.DataFrame
    cf: pd.DataFrame
    ratios: pd.DataFrame
    sectors: pd.DataFrame
    pros_cons: pd.DataFrame
    capital: pd.DataFrame


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], textColor=colors.white, fontSize=14, leading=16, alignment=TA_LEFT),
        "header_meta": ParagraphStyle("header_meta", parent=base["Title"], textColor=colors.white, fontSize=12, leading=14, alignment=TA_CENTER),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], textColor=NAVY, fontSize=11, leading=14, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["BodyText"], textColor=TEXT, fontSize=8, leading=10),
        "small": ParagraphStyle("small", parent=base["BodyText"], textColor=TEXT, fontSize=7, leading=9),
        "center": ParagraphStyle("center", parent=base["BodyText"], textColor=TEXT, fontSize=8, leading=10, alignment=TA_CENTER),
        "green": ParagraphStyle("green", parent=base["BodyText"], textColor=GREEN, fontSize=8, leading=10, bulletIndent=0),
        "red": ParagraphStyle("red", parent=base["BodyText"], textColor=RED, fontSize=8, leading=10, bulletIndent=0),
    }


def _p(text: object, style: ParagraphStyle) -> Paragraph:
    clean = "" if pd.isna(text) else str(text)
    return Paragraph(clean.replace("&", "&amp;"), style)


def _fmt(value: object, suffix: str = "", places: int = 1) -> str:
    if pd.isna(value):
        return "NA"
    try:
        return f"{float(value):,.{places}f}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def _clean_year(year: object) -> str:
    return "" if pd.isna(year) else str(year).replace("Mar-", "FY20")


def _sort_years(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "year" not in df:
        return df.copy()
    return df.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key)).copy()


def _latest_non_ttm(df: pd.DataFrame) -> pd.Series | None:
    if df.empty or "year" not in df:
        return None
    source = df[df["year"].astype(str).str.lower().ne("ttm")]
    if source.empty:
        return None
    return _sort_years(source).iloc[-1]


def load_report_data(db_path: Path = DB_PATH) -> ReportData:
    with sqlite3.connect(db_path) as conn:
        companies = pd.read_sql_query("SELECT * FROM companies", conn)
        pl = pd.read_sql_query("SELECT * FROM profitandloss", conn)
        bs = pd.read_sql_query("SELECT * FROM balancesheet", conn)
        cf = pd.read_sql_query("SELECT * FROM cashflow", conn)
        ratios = pd.read_sql_query("SELECT * FROM financial_ratios", conn)
        sectors = pd.read_sql_query("SELECT * FROM sectors", conn)

    pros_source = PROS_CONS_CANONICAL if PROS_CONS_CANONICAL.exists() else OUTPUT_DIR / "generated_pros_cons.csv"
    if not PROS_CONS_CANONICAL.exists() and pros_source.exists():
        shutil.copyfile(pros_source, PROS_CONS_CANONICAL)
    pros_cons = pd.read_csv(pros_source) if pros_source.exists() else pd.DataFrame(columns=["company_id", "type", "text"])

    capital_path = OUTPUT_DIR / "capital_allocation.csv"
    capital = pd.read_csv(capital_path) if capital_path.exists() else pd.DataFrame(columns=["company_id", "year", "pattern_label"])
    return ReportData(companies, pl, bs, cf, ratios, sectors, pros_cons, capital)


def sector_universe(data: ReportData) -> list[str]:
    return sorted(data.sectors["company_id"].dropna().astype(str).unique())


def _company_name(data: ReportData, ticker: str) -> str:
    row = data.companies[data.companies["id"].eq(ticker)]
    if row.empty or pd.isna(row.iloc[0].get("company_name")):
        return ticker
    return str(row.iloc[0]["company_name"])


def _sector(data: ReportData, ticker: str) -> str:
    row = data.sectors[data.sectors["company_id"].eq(ticker)]
    if row.empty or pd.isna(row.iloc[0].get("broad_sector")):
        return "Unassigned"
    return str(row.iloc[0]["broad_sector"])


def _company_frames(data: ReportData, ticker: str) -> dict[str, pd.DataFrame]:
    return {
        "pl": _sort_years(data.pl[data.pl["company_id"].eq(ticker)]),
        "bs": _sort_years(data.bs[data.bs["company_id"].eq(ticker)]),
        "cf": _sort_years(data.cf[data.cf["company_id"].eq(ticker)]),
        "ratios": _sort_years(data.ratios[data.ratios["company_id"].eq(ticker)]),
        "capital": _sort_years(data.capital[data.capital["company_id"].eq(ticker)]),
    }


def _line_chart(df: pd.DataFrame, ticker: str, tmp_dir: Path) -> Path:
    path = tmp_dir / f"{ticker}_roe_roce.png"
    source = df[df["year"].astype(str).str.lower().ne("ttm")].tail(10)
    years = [_clean_year(v) for v in source["year"]]
    fig, ax1 = plt.subplots(figsize=(6.7, 2.0), dpi=150)
    ax2 = ax1.twinx()
    ax1.plot(years, source.get("return_on_equity_pct", pd.Series(dtype=float)), color="#2563eb", marker="o", linewidth=1.8, label="ROE")
    ax2.plot(years, source.get("return_on_capital_employed_pct", pd.Series(dtype=float)), color="#f97316", marker="s", linewidth=1.8, label="ROCE")
    ax1.set_ylabel("ROE %", color="#2563eb", fontsize=8)
    ax2.set_ylabel("ROCE %", color="#f97316", fontsize=8)
    ax1.tick_params(axis="x", rotation=35, labelsize=7)
    ax1.tick_params(axis="y", labelsize=7)
    ax2.tick_params(axis="y", labelsize=7)
    ax1.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _bar_chart(df: pd.DataFrame, ticker: str, tmp_dir: Path) -> Path:
    path = tmp_dir / f"{ticker}_sales_profit.png"
    source = df[df["year"].astype(str).str.lower().ne("ttm")].tail(10)
    years = [_clean_year(v) for v in source["year"]]
    x = range(len(source))
    fig, ax = plt.subplots(figsize=(6.7, 2.2), dpi=150)
    ax.bar([i - 0.18 for i in x], source.get("sales", pd.Series(dtype=float)), width=0.36, color="#1d4ed8", label="Revenue")
    ax.bar([i + 0.18 for i in x], source.get("net_profit", pd.Series(dtype=float)), width=0.36, color="#16a34a", label="Net Profit")
    ax.set_xticks(list(x), years, rotation=35, ha="right", fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", alpha=0.22)
    ax.legend(fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _bs_chart(df: pd.DataFrame, ticker: str, tmp_dir: Path) -> Path:
    path = tmp_dir / f"{ticker}_bs.png"
    source = df[df["year"].astype(str).str.lower().ne("ttm")].tail(10)
    years = [_clean_year(v) for v in source["year"]]
    equity = source.get("equity_capital", 0).fillna(0) + source.get("reserves", 0).fillna(0)
    borrowings = source.get("borrowings", pd.Series([0] * len(source))).fillna(0)
    other = source.get("other_liabilities", pd.Series([0] * len(source))).fillna(0)
    fig, ax = plt.subplots(figsize=(6.7, 2.15), dpi=150)
    ax.bar(years, equity, color="#2563eb", label="Equity")
    ax.bar(years, borrowings, bottom=equity, color="#dc2626", label="Borrowings")
    ax.bar(years, other, bottom=equity + borrowings, color="#64748b", label="Other liabilities")
    ax.tick_params(axis="x", rotation=35, labelsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(fontsize=7, frameon=False, ncols=3)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _waterfall_chart(row: pd.Series | None, ticker: str, tmp_dir: Path) -> Path:
    path = tmp_dir / f"{ticker}_waterfall.png"
    labels = ["CFO", "CFI", "CFF", "Net CF"]
    values = [0, 0, 0, 0] if row is None else [row.get("operating_activity", 0), row.get("investing_activity", 0), row.get("financing_activity", 0), row.get("net_cash_flow", 0)]
    colors_ = ["#16a34a" if float(v or 0) >= 0 else "#dc2626" for v in values]
    fig, ax = plt.subplots(figsize=(3.2, 2.1), dpi=150)
    ax.bar(labels, values, color=colors_)
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.tick_params(axis="both", labelsize=7)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _kpi_tiles(frames: dict[str, pd.DataFrame], styles: dict[str, ParagraphStyle]) -> Table:
    pl = _latest_non_ttm(frames["pl"])
    ratios = _latest_non_ttm(frames["ratios"])
    cf = _latest_non_ttm(frames["cf"])
    capital = _latest_non_ttm(frames["capital"])
    values = [
        ("Revenue", _fmt(pl.get("sales") if pl is not None else None, " Cr", 0)),
        ("Net Profit", _fmt(pl.get("net_profit") if pl is not None else None, " Cr", 0)),
        ("ROE", _fmt(ratios.get("return_on_equity_pct") if ratios is not None else None, "%")),
        ("ROCE", _fmt(ratios.get("return_on_capital_employed_pct") if ratios is not None else None, "%")),
        ("FCF", _fmt(ratios.get("free_cash_flow_cr") if ratios is not None else None, " Cr", 0)),
        ("Capital Pattern", capital.get("pattern_label") if capital is not None else "NA"),
    ]
    cells = []
    for title, value in values:
        cells.append([_p(title, styles["small"]), _p(value, styles["center"])])
    table = Table(
        [[cells[0], cells[1], cells[2]], [cells[3], cells[4], cells[5]]],
        colWidths=[2.25 * inch] * 3,
        rowHeights=[0.58 * inch] * 2,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.4, GRID),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
            ]
        )
    )
    return table


def _header(company_name: str, ticker: str, sector: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[_p(f"{company_name} ({ticker})", styles["title"]), _p(sector, styles["header_meta"])]],
        colWidths=[5.2 * inch, 1.9 * inch],
        rowHeights=[0.55 * inch],
    )
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("WORDWRAP", (0, 0), (-1, -1), "CJK")]))
    return table


def _bullet_section(title: str, items: list[str], color: colors.Color, style: ParagraphStyle) -> list[Paragraph]:
    content = [Paragraph(f"<b>{title}</b>", ParagraphStyle(f"{title}h", parent=style, textColor=color, fontSize=10, leading=12))]
    for item in items[:4]:
        content.append(Paragraph(item, style, bulletText="-"))
    if not items:
        content.append(Paragraph("No generated items available.", style))
    return content


def _pros_cons(data: ReportData, ticker: str) -> tuple[list[str], list[str]]:
    rows = data.pros_cons[data.pros_cons["company_id"].astype(str).eq(ticker)] if not data.pros_cons.empty else pd.DataFrame()
    type_col = "type" if "type" in rows.columns else "sentiment"
    pros = rows[rows[type_col].eq("pro")]["text"].dropna().astype(str).tolist() if type_col in rows else []
    cons = rows[rows[type_col].eq("con")]["text"].dropna().astype(str).tolist() if type_col in rows else []
    return pros, cons


def build_tearsheet(ticker: str, output_path: Path, data: ReportData | None = None) -> Path:
    data = data or load_report_data()
    styles = _styles()
    frames = _company_frames(data, ticker)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    company_name = _company_name(data, ticker)
    sector = _sector(data, ticker)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        bar = _bar_chart(frames["pl"], ticker, tmp_dir)
        line = _line_chart(frames["ratios"], ticker, tmp_dir)
        bs_chart = _bs_chart(frames["bs"], ticker, tmp_dir)
        waterfall = _waterfall_chart(_latest_non_ttm(frames["cf"]), ticker, tmp_dir)
        latest_capital = _latest_non_ttm(frames["capital"])
        badge = latest_capital.get("pattern_label") if latest_capital is not None else "NA"
        pros, cons = _pros_cons(data, ticker)

        story = [
            _header(company_name, ticker, sector, styles),
            Spacer(1, 0.15 * inch),
            _kpi_tiles(frames, styles),
            Spacer(1, 0.16 * inch),
            _p("10-year Revenue and Net Profit", styles["h2"]),
            Image(str(bar), width=6.9 * inch, height=2.15 * inch),
            Spacer(1, 0.08 * inch),
            _p("ROE and ROCE Trend", styles["h2"]),
            Image(str(line), width=6.9 * inch, height=1.95 * inch),
            PageBreak(),
            _header(company_name, ticker, sector, styles),
            Spacer(1, 0.13 * inch),
            _p("Balance Sheet Composition", styles["h2"]),
            Image(str(bs_chart), width=6.9 * inch, height=1.95 * inch),
            Spacer(1, 0.2 * inch),
            Table(
                [[Image(str(waterfall), width=3.15 * inch, height=2.05 * inch), _bullet_section("Pros", pros, GREEN, styles["green"]), _bullet_section("Cons", cons, RED, styles["red"])]],
                colWidths=[3.25 * inch, 1.9 * inch, 1.9 * inch],
                rowHeights=[2.35 * inch],
            ),
            Spacer(1, 0.12 * inch),
            Table([[_p("Capital Allocation", styles["center"]), _p(badge, styles["center"])]], colWidths=[2.0 * inch, 5.0 * inch], rowHeights=[0.35 * inch]),
        ]
        story[-3].setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("WORDWRAP", (0, 0), (-1, -1), "CJK")]))
        story[-1].setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG), ("GRID", (0, 0), (-1, -1), 0.4, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("WORDWRAP", (0, 0), (-1, -1), "CJK")]))
        doc = SimpleDocTemplate(str(output_path), pagesize=A4, rightMargin=0.45 * inch, leftMargin=0.45 * inch, topMargin=0.35 * inch, bottomMargin=0.35 * inch)
        doc.build(story)
    return output_path


def validate_pdf(path: Path, expected_pages: int | None = None, min_size_kb: int | None = None) -> dict[str, object]:
    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    text_lengths = [len(page.extract_text() or "") for page in reader.pages]
    size_kb = path.stat().st_size / 1024
    return {
        "path": str(path),
        "page_count": page_count,
        "size_kb": round(size_kb, 1),
        "blank_pages": sum(1 for length in text_lengths if length < 20),
        "expected_pages_ok": expected_pages is None or page_count == expected_pages,
        "min_size_ok": min_size_kb is None or size_kb >= min_size_kb,
    }


def generate_batch_tearsheets(data: ReportData | None = None) -> pd.DataFrame:
    data = data or load_report_data()
    TEARSHEET_DIR.mkdir(parents=True, exist_ok=True)
    skipped = []
    for ticker in sector_universe(data):
        pl_years = data.pl[data.pl["company_id"].eq(ticker)]["year"].dropna().nunique()
        if pl_years < 3:
            skipped.append({"company_id": ticker, "reason": f"Only {pl_years} years of P&L data"})
            continue
        build_tearsheet(ticker, TEARSHEET_DIR / f"{ticker}_tearsheet.pdf", data)
    skipped_df = pd.DataFrame(skipped, columns=["company_id", "reason"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    skipped_df.to_csv(SKIPPED_CSV, index=False)
    return skipped_df


def _metric_row(data: ReportData, ticker: str) -> dict[str, object]:
    frames = _company_frames(data, ticker)
    pl = _latest_non_ttm(frames["pl"])
    ratios = _latest_non_ttm(frames["ratios"])
    capital = _latest_non_ttm(frames["capital"])
    return {
        "ticker": ticker,
        "company": _company_name(data, ticker),
        "sector": _sector(data, ticker),
        "revenue": pl.get("sales") if pl is not None else None,
        "net_profit": pl.get("net_profit") if pl is not None else None,
        "roe": ratios.get("return_on_equity_pct") if ratios is not None else None,
        "roce": ratios.get("return_on_capital_employed_pct") if ratios is not None else None,
        "debt_to_equity": ratios.get("debt_to_equity") if ratios is not None else None,
        "fcf": ratios.get("free_cash_flow_cr") if ratios is not None else None,
        "revenue_cagr_5yr": ratios.get("revenue_cagr_5yr") if ratios is not None else None,
        "capital_pattern": capital.get("pattern_label") if capital is not None else None,
    }


def generate_sector_reports(data: ReportData | None = None) -> list[Path]:
    data = data or load_report_data()
    SECTOR_DIR.mkdir(parents=True, exist_ok=True)
    styles = _styles()
    rows = pd.DataFrame([_metric_row(data, ticker) for ticker in sector_universe(data)])
    paths = []
    sector_groups = [(sector, group) for sector, group in rows.groupby("sector", sort=True)]
    sector_groups.append(("All Sectors", rows))
    for sector, group in sector_groups:
        safe = str(sector).replace("/", "_").replace(" ", "_")
        path = SECTOR_DIR / f"{safe}_report.pdf"
        med = group[["revenue", "net_profit", "roe", "roce", "debt_to_equity", "fcf", "revenue_cagr_5yr"]].median(numeric_only=True)
        table_rows = [[_p(col, styles["small"]) for col in ["Ticker", "Company", "Revenue", "PAT", "ROE", "ROCE", "D/E", "FCF", "Rev CAGR"]]]
        for row in group.sort_values("ticker").itertuples(index=False):
            table_rows.append([_p(row.ticker, styles["small"]), _p(row.company, styles["small"]), _p(_fmt(row.revenue, "", 0), styles["small"]), _p(_fmt(row.net_profit, "", 0), styles["small"]), _p(_fmt(row.roe, "%"), styles["small"]), _p(_fmt(row.roce, "%"), styles["small"]), _p(_fmt(row.debt_to_equity, "x"), styles["small"]), _p(_fmt(row.fcf, "", 0), styles["small"]), _p(_fmt(row.revenue_cagr_5yr, "%"), styles["small"])])
        summary = Table(
            [[_p("Median Revenue", styles["center"]), _p("Median PAT", styles["center"]), _p("Median ROE", styles["center"]), _p("Median ROCE", styles["center"])], [_p(_fmt(med.get("revenue"), "", 0), styles["center"]), _p(_fmt(med.get("net_profit"), "", 0), styles["center"]), _p(_fmt(med.get("roe"), "%"), styles["center"]), _p(_fmt(med.get("roce"), "%"), styles["center"])]],
            colWidths=[2.4 * inch] * 4,
        )
        summary.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG), ("WORDWRAP", (0, 0), (-1, -1), "CJK")]))
        table = Table(table_rows, colWidths=[0.7 * inch, 1.75 * inch, 0.88 * inch, 0.78 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.82 * inch, 0.85 * inch], repeatRows=1)
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, GRID), ("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("WORDWRAP", (0, 0), (-1, -1), "CJK")]))
        doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=0.35 * inch, leftMargin=0.35 * inch, topMargin=0.35 * inch, bottomMargin=0.35 * inch)
        doc.build([_p(f"{sector} Sector Report", ParagraphStyle("sector", parent=styles["title"], textColor=NAVY)), Spacer(1, 0.15 * inch), summary, Spacer(1, 0.18 * inch), table])
        paths.append(path)
    return paths


def _arrow(current: object, previous: object) -> str:
    if pd.isna(current) or pd.isna(previous):
        return "->"
    current_value = float(current)
    previous_value = float(previous)
    if previous_value == 0:
        return "->"
    change = (current_value - previous_value) / abs(previous_value)
    if change > 0.02:
        return "^"
    if change < -0.02:
        return "v"
    return "->"


def generate_portfolio_summary(data: ReportData | None = None) -> Path:
    data = data or load_report_data()
    PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    path = PORTFOLIO_DIR / "portfolio_summary.pdf"
    styles = _styles()
    story = []
    for idx, ticker in enumerate(sector_universe(data)):
        frames = _company_frames(data, ticker)
        pl = _sort_years(frames["pl"][frames["pl"]["year"].astype(str).str.lower().ne("ttm")]).tail(2)
        ratios = _sort_years(frames["ratios"][frames["ratios"]["year"].astype(str).str.lower().ne("ttm")]).tail(2)
        latest = _metric_row(data, ticker)
        prev_pl = pl.iloc[0] if len(pl) == 2 else None
        prev_ratios = ratios.iloc[0] if len(ratios) == 2 else None
        metrics = [
            ("Revenue", latest["revenue"], _arrow(latest["revenue"], prev_pl.get("sales") if prev_pl is not None else None)),
            ("Net Profit", latest["net_profit"], _arrow(latest["net_profit"], prev_pl.get("net_profit") if prev_pl is not None else None)),
            ("ROE", latest["roe"], _arrow(latest["roe"], prev_ratios.get("return_on_equity_pct") if prev_ratios is not None else None)),
            ("ROCE", latest["roce"], _arrow(latest["roce"], prev_ratios.get("return_on_capital_employed_pct") if prev_ratios is not None else None)),
            ("D/E", latest["debt_to_equity"], _arrow(latest["debt_to_equity"], prev_ratios.get("debt_to_equity") if prev_ratios is not None else None)),
            ("FCF", latest["fcf"], _arrow(latest["fcf"], prev_ratios.get("free_cash_flow_cr") if prev_ratios is not None else None)),
        ]
        story.extend([_header(_company_name(data, ticker), ticker, _sector(data, ticker), styles), Spacer(1, 0.25 * inch)])
        rows = [[_p("Metric", styles["center"]), _p("Latest", styles["center"]), _p("Trend", styles["center"])]]
        rows += [[_p(name, styles["body"]), _p(_fmt(value), styles["body"]), _p(arrow, styles["center"])] for name, value, arrow in metrics]
        table = Table(rows, colWidths=[2.3 * inch, 2.3 * inch, 1.2 * inch])
        table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, GRID), ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG), ("WORDWRAP", (0, 0), (-1, -1), "CJK")]))
        story.append(table)
        if idx < len(sector_universe(data)) - 1:
            story.append(PageBreak())
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=0.5 * inch, leftMargin=0.5 * inch, topMargin=0.45 * inch, bottomMargin=0.45 * inch)
    doc.build(story)
    return path


def generate_all() -> dict[str, object]:
    data = load_report_data()
    skipped = generate_batch_tearsheets(data)
    sector_paths = generate_sector_reports(data)
    portfolio_path = generate_portfolio_summary(data)
    return {
        "skipped": skipped,
        "tearsheet_count": len(list(TEARSHEET_DIR.glob("*_tearsheet.pdf"))),
        "sector_count": len(sector_paths),
        "portfolio_path": portfolio_path,
    }


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate Sprint 5 PDF reports.")
    parser.add_argument("--ticker", help="Generate one company tearsheet")
    parser.add_argument("--all", action="store_true", help="Generate all tearsheets, sector reports, and portfolio summary")
    args = parser.parse_args(list(argv) if argv is not None else None)

    data = load_report_data()
    if args.ticker:
        path = build_tearsheet(args.ticker.upper(), TEARSHEET_DIR / f"{args.ticker.upper()}_tearsheet.pdf", data)
        print(validate_pdf(path, expected_pages=2))
    elif args.all:
        result = generate_all()
        print(result)
    else:
        for ticker in ["TCS", "HDFCBANK", "RELIANCE", "SUNPHARMA", "TATASTEEL"]:
            path = build_tearsheet(ticker, TEARSHEET_DIR / f"{ticker}_tearsheet.pdf", data)
            print(validate_pdf(path, expected_pages=2))


if __name__ == "__main__":
    main()
