"""Generate deterministic pros and cons from computed financial metrics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
import sqlite3

import pandas as pd

from src.analytics.cagr import fiscal_year_sort_key


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "db" / "nifty100.db"
OUTPUT_DIR = ROOT / "output"
GENERATED_CSV = OUTPUT_DIR / "generated_pros_cons.csv"
CANONICAL_GENERATED_CSV = OUTPUT_DIR / "pros_cons_generated.csv"
SUMMARY_CSV = OUTPUT_DIR / "generated_pros_cons_summary.csv"

Sentiment = Literal["pro", "con"]


@dataclass(frozen=True)
class Rule:
    rule_id: str
    sentiment: Sentiment
    text: str
    evaluator: Callable[[pd.DataFrame], tuple[bool, float, str, str | None]]


def _result(matched: bool, confidence: float, evidence: str, text: str | None = None) -> tuple[bool, float, str, str | None]:
    return matched, confidence, evidence, text


def _num(value: object) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence(value: float, threshold: float, scale: float, higher_is_better: bool = True) -> float:
    distance = value - threshold if higher_is_better else threshold - value
    return round(max(0.6, min(0.98, 0.7 + distance / scale)), 2)


def _trend_confidence(delta: float, scale: float = 100.0, base: float = 0.72) -> float:
    return round(max(0.61, min(0.98, base + abs(delta) / scale)), 2)


def _latest_metric_row(history: pd.DataFrame) -> pd.Series | None:
    fiscal = history[history["year"].astype(str).str.lower().ne("ttm")]
    source = fiscal if not fiscal.empty else history
    if source.empty:
        return None
    ordered = source.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key))
    return ordered.iloc[-1]


def _latest_available_row(history: pd.DataFrame) -> pd.Series | None:
    if history.empty:
        return None
    ordered = history.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key))
    return ordered.iloc[-1]


def _latest_value(history: pd.DataFrame, column: str, include_ttm: bool = False) -> tuple[float | None, str | None]:
    row = _latest_available_row(history) if include_ttm else _latest_metric_row(history)
    if row is None or column not in row:
        return None, None
    return _num(row[column]), str(row["year"])


def _latest_text_value(history: pd.DataFrame, column: str) -> str | None:
    row = _latest_metric_row(history)
    if row is None or column not in row or pd.isna(row[column]):
        return None
    return str(row[column])


def _last_values(history: pd.DataFrame, column: str, count: int, include_ttm: bool = False) -> list[float]:
    source = history if include_ttm else history[history["year"].astype(str).str.lower().ne("ttm")]
    if column not in source:
        return []
    ordered = source.sort_values("year", key=lambda values: values.map(fiscal_year_sort_key))
    values = [_num(value) for value in ordered[column].tail(count)]
    return [value for value in values if value is not None]


def _consecutive_positive(history: pd.DataFrame, column: str, years: int) -> tuple[bool, float, str]:
    values = _last_values(history, column, years)
    matched = len(values) >= years and all(value > 0 for value in values)
    confidence = round(min(0.98, 0.7 + len(values) * 0.04), 2) if matched else 0.0
    return _result(matched, confidence, f"latest_{years}_values={values}")


def _consecutive_negative(history: pd.DataFrame, column: str, years: int) -> tuple[bool, float, str]:
    values = _last_values(history, column, years)
    matched = len(values) >= years and all(value < 0 for value in values)
    confidence = round(min(0.98, 0.72 + len(values) * 0.04), 2) if matched else 0.0
    return _result(matched, confidence, f"latest_{years}_values={values}")


def _above_latest(column: str, threshold: float, scale: float, include_ttm: bool = False):
    def evaluator(history: pd.DataFrame) -> tuple[bool, float, str]:
        value, year = _latest_value(history, column, include_ttm=include_ttm)
        matched = value is not None and value > threshold
        confidence = _confidence(value, threshold, scale) if matched else 0.0
        return _result(matched, confidence, f"{column}={value}, year={year}, threshold>{threshold}")

    return evaluator


def _below_latest(column: str, threshold: float, scale: float, include_ttm: bool = False):
    def evaluator(history: pd.DataFrame) -> tuple[bool, float, str]:
        value, year = _latest_value(history, column, include_ttm=include_ttm)
        matched = value is not None and value < threshold
        confidence = _confidence(value, threshold, scale, higher_is_better=False) if matched else 0.0
        return _result(matched, confidence, f"{column}={value}, year={year}, threshold<{threshold}")

    return evaluator


def _roe_sustained_above_20(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    values = _last_values(history, "return_on_equity_pct", 3)
    matched = len(values) == 3 and all(value > 20 for value in values)
    confidence = _confidence(min(values), 20, 30) if matched else 0.0
    return _result(matched, confidence, f"last_3_roe={values}")


def _debt_free(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "debt_to_equity")
    matched = value is not None and value == 0
    return _result(matched, 0.95 if matched else 0.0, f"debt_to_equity={value}, year={year}")


def _high_debt_non_financial(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "debt_to_equity")
    sector = _latest_text_value(history, "broad_sector")
    is_financial = sector is not None and sector.strip().lower() == "financials"
    matched = value is not None and value > 2 and not is_financial
    confidence = _confidence(value, 2, 3) if matched else 0.0
    text = f"Debt-to-equity ratio of {value:.2f} is elevated for a non-financial company and warrants monitoring" if matched else None
    return _result(matched, confidence, f"debt_to_equity={value}, broad_sector={sector}, year={year}, threshold>2", text)


def _icr_strong(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "interest_coverage")
    label_value, _ = _latest_value(history, "debt_to_equity")
    icr_label = None
    row = _latest_metric_row(history)
    if row is not None and "icr_label" in row and pd.notna(row["icr_label"]):
        icr_label = str(row["icr_label"])
    matched = icr_label == "Debt Free" or (value is not None and value > 10) or label_value == 0
    confidence = 0.94 if icr_label == "Debt Free" or label_value == 0 else _confidence(value or 0, 10, 30)
    return _result(matched, confidence if matched else 0.0, f"interest_coverage={value}, icr_label={icr_label}, year={year}")


def _icr_weak(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "interest_coverage")
    matched = value is not None and value < 1.5
    confidence = _confidence(value, 1.5, 3, higher_is_better=False) if matched else 0.0
    return _result(matched, confidence, f"interest_coverage={value}, year={year}, threshold<1.5")


def _dividend_backed_by_fcf(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    dividend, year = _latest_value(history, "dividend_yield")
    fcf, _ = _latest_value(history, "free_cash_flow_cr")
    matched = dividend is not None and dividend > 2 and fcf is not None and fcf > 0
    confidence = min(_confidence(dividend, 2, 5), _confidence(fcf, 0, max(abs(fcf), 1))) if matched else 0.0
    return _result(matched, confidence, f"dividend_yield={dividend}, free_cash_flow_cr={fcf}, year={year}")


def _roe_improving(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    values = _last_values(history, "return_on_equity_pct", 3)
    matched = len(values) == 3 and values[0] < values[1] < values[2]
    confidence = round(min(0.95, 0.76 + (values[-1] - values[0]) / 50), 2) if matched else 0.0
    return _result(matched, confidence, f"last_3_roe={values}")


def _revenue_slower_than_profit(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    revenue, revenue_year = _latest_value(history, "revenue_cagr_5yr", include_ttm=True)
    pat, pat_year = _latest_value(history, "pat_cagr_5yr", include_ttm=True)
    matched = revenue is not None and pat is not None and revenue > 0 and pat > revenue
    confidence = _trend_confidence((pat or 0) - (revenue or 0), scale=50, base=0.7) if matched else 0.0
    return _result(matched, confidence, f"revenue_cagr_5yr={revenue}, pat_cagr_5yr={pat}, years={revenue_year}/{pat_year}")


def _assets_growing_debt_declining(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    assets = _last_values(history, "total_assets", 3)
    debt = _last_values(history, "borrowings", 3)
    matched = len(assets) == 3 and len(debt) == 3 and assets[0] < assets[1] < assets[2] and debt[0] > debt[1] > debt[2]
    asset_delta = assets[-1] - assets[0] if len(assets) == 3 else 0
    debt_delta = debt[0] - debt[-1] if len(debt) == 3 else 0
    confidence = _trend_confidence(asset_delta + debt_delta, scale=max(abs(assets[0]) + abs(debt[0]), 1), base=0.76) if matched else 0.0
    return _result(matched, confidence, f"last_3_total_assets={assets}, last_3_borrowings={debt}")


def _opm_declining_3yr(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    values = _last_values(history, "operating_profit_margin_pct", 3)
    matched = len(values) == 3 and values[0] > values[1] > values[2]
    confidence = _trend_confidence(values[0] - values[-1], scale=30, base=0.74) if matched else 0.0
    return _result(matched, confidence, f"last_3_opm={values}")


def _latest_net_loss(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "net_profit")
    matched = value is not None and value < 0
    confidence = _confidence(value, 0, max(abs(value), 1), higher_is_better=False) if matched else 0.0
    return _result(matched, confidence, f"net_profit={value}, year={year}")


def _revenue_declining_2yr(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    values = _last_values(history, "sales", 3)
    matched = len(values) == 3 and values[0] > values[1] > values[2]
    confidence = _trend_confidence(values[0] - values[-1], scale=max(abs(values[0]), 1), base=0.74) if matched else 0.0
    return _result(matched, confidence, f"last_3_sales={values}")


def _dividend_payout_above_100(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "dividend_payout_ratio_pct")
    if value is None:
        value, year = _latest_value(history, "dividend_payout")
    matched = value is not None and value > 100
    confidence = _confidence(value, 100, 150) if matched else 0.0
    return _result(matched, confidence, f"dividend_payout_ratio_pct={value}, year={year}, threshold>100")


def _debt_to_equity_rising_3yr(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    values = _last_values(history, "debt_to_equity", 3)
    matched = len(values) == 3 and values[0] < values[1] < values[2]
    confidence = _trend_confidence(values[-1] - values[0], scale=3, base=0.74) if matched else 0.0
    return _result(matched, confidence, f"last_3_debt_to_equity={values}")


def _eps_declining_3yr(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    values = _last_values(history, "earnings_per_share", 3)
    matched = len(values) == 3 and values[0] > values[1] > values[2]
    confidence = _trend_confidence(values[0] - values[-1], scale=max(abs(values[0]), 1), base=0.74) if matched else 0.0
    return _result(matched, confidence, f"last_3_eps={values}")


def _roce_below_10(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    value, year = _latest_value(history, "return_on_capital_employed_pct")
    matched = value is not None and value < 10
    confidence = _confidence(value, 10, 20, higher_is_better=False) if matched else 0.0
    return _result(matched, confidence, f"return_on_capital_employed_pct={value}, year={year}, threshold<10")


def _net_debt_above_3x_ebitda(history: pd.DataFrame) -> tuple[bool, float, str, str | None]:
    row = _latest_metric_row(history)
    if row is None:
        return _result(False, 0.0, "no_latest_row")
    net_debt_value = _num(row.get("net_debt_cr"))
    operating_profit = _num(row.get("operating_profit"))
    depreciation = _num(row.get("depreciation"))
    ebitda = (operating_profit or 0.0) + (depreciation or 0.0)
    ratio = net_debt_value / ebitda if net_debt_value is not None and ebitda > 0 else None
    matched = ratio is not None and ratio > 3
    confidence = _confidence(ratio, 3, 4) if matched else 0.0
    return _result(matched, confidence, f"net_debt_cr={net_debt_value}, ebitda={ebitda}, net_debt_to_ebitda={ratio}, year={row.get('year')}")


PRO_RULES: tuple[Rule, ...] = (
    Rule("PRO_01", "pro", "Consistently high return on equity above 20% demonstrates exceptional capital efficiency", _roe_sustained_above_20),
    Rule("PRO_02", "pro", "Strong free cash flow generation over 5 years signals healthy business fundamentals", lambda h: _consecutive_positive(h, "free_cash_flow_cr", 5)),
    Rule("PRO_03", "pro", "Debt-free balance sheet provides financial flexibility and eliminates interest burden", _debt_free),
    Rule("PRO_04", "pro", "Revenue growing at above 15% CAGR over 5 years reflects strong business momentum", _above_latest("revenue_cagr_5yr", 15, 35, include_ttm=True)),
    Rule("PRO_05", "pro", "Operating profit margin above 25% indicates strong pricing power and cost discipline", _above_latest("operating_profit_margin_pct", 25, 40)),
    Rule("PRO_06", "pro", "Net profit compounding at above 20% over 5 years creates significant shareholder value", _above_latest("pat_cagr_5yr", 20, 40, include_ttm=True)),
    Rule("PRO_07", "pro", "Very high interest coverage ratio reflects negligible financial stress from debt servicing", _icr_strong),
    Rule("PRO_08", "pro", "Consistent dividend yield above 2% backed by positive free cash flow", _dividend_backed_by_fcf),
    Rule("PRO_09", "pro", "Earnings per share growing above 15% CAGR indicates strong earnings quality and compounding", _above_latest("eps_cagr_5yr", 15, 35, include_ttm=True)),
    Rule("PRO_10", "pro", "Return on equity improving for 3 consecutive years shows strengthening business quality", _roe_improving),
    Rule("PRO_11", "pro", "Revenue growing slower than profits shows improving operating leverage and scale benefits", _revenue_slower_than_profit),
    Rule("PRO_12", "pro", "Growing asset base funded by internal accruals reflects self-sustaining growth", _assets_growing_debt_declining),
)

CON_RULES: tuple[Rule, ...] = (
    Rule("CON_01", "con", "Debt-to-equity ratio is elevated for a non-financial company and warrants monitoring", _high_debt_non_financial),
    Rule("CON_02", "con", "Free cash flow negative for 3 consecutive years raises concern about cash generation quality", lambda h: _consecutive_negative(h, "free_cash_flow_cr", 3)),
    Rule("CON_03", "con", "Operating margins declining for 3 consecutive years suggest pricing or cost pressure", _opm_declining_3yr),
    Rule("CON_04", "con", "Company reported a net loss in the most recent financial year", _latest_net_loss),
    Rule("CON_05", "con", "Revenue contraction over 2 consecutive years indicates demand weakness or market share loss", _revenue_declining_2yr),
    Rule("CON_06", "con", "Interest coverage ratio below 1.5x indicates the company is at risk of not meeting its debt obligations", _icr_weak),
    Rule("CON_07", "con", "Dividend payout ratio above 100% means the company is paying dividends from reserves, which is unsustainable", _dividend_payout_above_100),
    Rule("CON_08", "con", "Rising debt-to-equity ratio over 3 years suggests increasing financial leverage risk", _debt_to_equity_rising_3yr),
    Rule("CON_09", "con", "Earnings per share declining for 3 consecutive years reflects deteriorating profitability", _eps_declining_3yr),
    Rule("CON_10", "con", "Return on capital employed below 10% suggests the business is not generating sufficient returns on invested capital", _roce_below_10),
    Rule("CON_11", "con", "Net debt exceeding 3 times EBITDA is a high leverage ratio and limits financial flexibility", _net_debt_above_3x_ebitda),
    Rule("CON_12", "con", "Revenue growing at below 5% over 5 years lags inflation and suggests limited business momentum", _below_latest("revenue_cagr_5yr", 5, 20, include_ttm=True)),
)

ALL_RULES: tuple[Rule, ...] = PRO_RULES + CON_RULES


def load_ratio_history(db_path: Path = DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(
            """
            WITH yearly_ratios AS (
                SELECT
                    fr.*,
                    CAST(substr(CAST(fr.year AS TEXT), -4) AS INTEGER) AS fiscal_year
                FROM financial_ratios fr
            )
            SELECT
                c.id AS company_id,
                yr.year,
                s.broad_sector,
                yr.return_on_equity_pct,
                yr.return_on_capital_employed_pct,
                yr.free_cash_flow_cr,
                yr.debt_to_equity,
                yr.revenue_cagr_5yr,
                yr.operating_profit_margin_pct,
                yr.pat_cagr_5yr,
                yr.interest_coverage,
                yr.icr_label,
                yr.dividend_yield,
                yr.eps_cagr_5yr,
                yr.earnings_per_share,
                yr.dividend_payout_ratio_pct,
                yr.net_debt_cr,
                pl.sales,
                pl.operating_profit,
                pl.depreciation,
                pl.net_profit,
                pl.eps,
                pl.dividend_payout,
                bs.borrowings,
                bs.total_assets
            FROM companies c
            LEFT JOIN sectors s
                ON s.company_id = c.id
            LEFT JOIN yearly_ratios yr
                ON yr.company_id = c.id
            LEFT JOIN profitandloss pl
                ON pl.company_id = c.id
               AND pl.year = yr.fiscal_year
            LEFT JOIN balancesheet bs
                ON bs.company_id = c.id
               AND bs.year = yr.fiscal_year
            ORDER BY c.id, yr.year
            """,
            conn,
        )


def generate_for_company(history: pd.DataFrame, rules: tuple[Rule, ...] = ALL_RULES) -> pd.DataFrame:
    if history.empty:
        return pd.DataFrame(columns=["company_id", "type", "rule_id", "text", "confidence_pct"])

    company_id = str(history["company_id"].dropna().iloc[0])
    rows: list[dict[str, object]] = []
    metric_history = history.dropna(subset=["year"]).copy()

    for rule in rules:
        matched, confidence, evidence, text = rule.evaluator(metric_history)
        confidence_pct = round(confidence * 100, 0)
        if matched and confidence_pct > 60:
            rows.append(
                {
                    "company_id": company_id,
                    "type": rule.sentiment,
                    "rule_id": rule.rule_id,
                    "text": text or rule.text,
                    "confidence_pct": int(confidence_pct),
                }
            )

    return pd.DataFrame(rows, columns=["company_id", "type", "rule_id", "text", "confidence_pct"])


def _coverage_fallback(company_history: pd.DataFrame, sentiment: Sentiment) -> dict[str, object]:
    company_id = str(company_history["company_id"].dropna().iloc[0])
    metric_history = company_history.dropna(subset=["year"]).copy()
    row = _latest_metric_row(metric_history)

    if sentiment == "pro":
        if row is not None and _num(row.get("net_profit")) is not None and (_num(row.get("net_profit")) or 0) > 0:
            text = "Company reported positive net profit in the most recent financial year, providing a baseline profitability signal"
        elif row is not None and _num(row.get("sales")) is not None and (_num(row.get("sales")) or 0) > 0:
            text = "Company generated positive revenue in the most recent financial year, indicating an active operating base"
        else:
            text = "Company remains in the covered universe, but financial history is limited for stronger positive rule matching"
        rule_id = "PRO_COVERAGE"
    else:
        debt_to_equity = _num(row.get("debt_to_equity")) if row is not None else None
        fcf = _num(row.get("free_cash_flow_cr")) if row is not None else None
        net_profit = _num(row.get("net_profit")) if row is not None else None
        if debt_to_equity is not None and debt_to_equity > 0:
            text = "Company carries balance sheet debt, so leverage should be monitored even though no major debt threshold was breached"
        elif fcf is not None and net_profit is not None and fcf < net_profit:
            text = "Free cash flow trails reported profit, warranting monitoring of cash conversion quality"
        else:
            text = "No high-confidence con rule triggered, but periodic monitoring remains warranted as financial conditions can change"
        rule_id = "CON_COVERAGE"

    return {
        "company_id": company_id,
        "type": sentiment,
        "rule_id": rule_id,
        "text": text,
        "confidence_pct": 61,
    }


def _ensure_company_coverage(history: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    existing = details.groupby(["company_id", "type"]).size() if not details.empty else pd.Series(dtype=int)

    for company_id, group in history.groupby("company_id", sort=True):
        company_key = str(company_id)
        for sentiment in ("pro", "con"):
            if (company_key, sentiment) not in existing.index:
                rows.append(_coverage_fallback(group, sentiment))

    if not rows:
        return details
    return pd.concat([details, pd.DataFrame(rows)], ignore_index=True)


def generate_pros_cons(db_path: Path = DB_PATH, output_dir: Path = OUTPUT_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    output_dir.mkdir(exist_ok=True)
    history = load_ratio_history(db_path)
    company_ids = pd.DataFrame({"company_id": sorted(history["company_id"].dropna().astype(str).unique())})

    generated = []
    for _, group in history.groupby("company_id", sort=True):
        generated.append(generate_for_company(group))
    details = pd.concat(generated, ignore_index=True) if generated else pd.DataFrame()

    if details.empty:
        details = pd.DataFrame(columns=["company_id", "type", "rule_id", "text", "confidence_pct"])
    details = _ensure_company_coverage(history, details)
    details = details.sort_values(["company_id", "type", "rule_id"]).reset_index(drop=True)

    summary = (
        details.pivot_table(
            index="company_id",
            columns="type",
            values="text",
            aggfunc=lambda values: " | ".join(values),
            fill_value="",
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )
    summary = company_ids.merge(summary, on="company_id", how="left")
    for column in ("pro", "con"):
        if column not in summary.columns:
            summary[column] = ""
        summary[column] = summary[column].fillna("")
    summary = summary.rename(columns={"pro": "pros", "con": "cons"})[["company_id", "pros", "cons"]]

    details.to_csv(output_dir / GENERATED_CSV.name, index=False)
    details.to_csv(output_dir / CANONICAL_GENERATED_CSV.name, index=False)
    summary.to_csv(output_dir / SUMMARY_CSV.name, index=False)
    return details, summary


def main() -> None:
    details, summary = generate_pros_cons()
    print(f"Wrote {GENERATED_CSV}: {len(details)} generated rule matches")
    print(f"Wrote {CANONICAL_GENERATED_CSV}: {len(details)} generated rule matches")
    print(f"Wrote {SUMMARY_CSV}: {len(summary)} company summaries")


if __name__ == "__main__":
    main()
