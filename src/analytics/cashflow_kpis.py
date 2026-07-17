"""Cash flow KPI formulas and capital allocation classification."""

from __future__ import annotations

from math import isfinite


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
