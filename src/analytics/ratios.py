"""Financial ratio formulas used by the Sprint 2 ratio engine."""

from __future__ import annotations

from dataclasses import dataclass
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


def pct(numerator: float | int | None, denominator: float | int | None) -> float | None:
    numerator = _num(numerator)
    denominator = _num(denominator)
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100


def net_profit_margin(net_profit: float | int | None, sales: float | int | None) -> float | None:
    return pct(net_profit, sales)


@dataclass(frozen=True)
class OpmResult:
    value: float | None
    source_difference_pct: float | None
    mismatch: bool


def operating_profit_margin(
    operating_profit: float | int | None,
    sales: float | int | None,
    source_opm_percentage: float | int | None = None,
    tolerance_pct: float = 1.0,
) -> OpmResult:
    value = pct(operating_profit, sales)
    source = _num(source_opm_percentage)
    diff = None
    mismatch = False
    if value is not None and source is not None:
        diff = abs(value - source)
        mismatch = diff > tolerance_pct
    return OpmResult(value=value, source_difference_pct=diff, mismatch=mismatch)


def equity_base(equity_capital: float | int | None, reserves: float | int | None) -> float | None:
    equity = _num(equity_capital) or 0.0
    reserve_value = _num(reserves) or 0.0
    return equity + reserve_value


def return_on_equity(
    net_profit: float | int | None,
    equity_capital: float | int | None,
    reserves: float | int | None,
) -> float | None:
    denominator = equity_base(equity_capital, reserves)
    if denominator is None or denominator <= 0:
        return None
    return pct(net_profit, denominator)


def return_on_capital_employed(
    ebit: float | int | None,
    equity_capital: float | int | None,
    reserves: float | int | None,
    borrowings: float | int | None,
) -> float | None:
    capital = (equity_base(equity_capital, reserves) or 0.0) + (_num(borrowings) or 0.0)
    if capital <= 0:
        return None
    return pct(ebit, capital)


def return_on_assets(net_profit: float | int | None, total_assets: float | int | None) -> float | None:
    return pct(net_profit, total_assets)


def debt_to_equity(
    borrowings: float | int | None,
    equity_capital: float | int | None,
    reserves: float | int | None,
) -> float | None:
    debt = _num(borrowings) or 0.0
    if debt == 0:
        return 0.0
    denominator = equity_base(equity_capital, reserves)
    if denominator is None or denominator <= 0:
        return None
    return debt / denominator


def high_leverage_flag(debt_to_equity_value: float | None, broad_sector: str | None) -> bool:
    if broad_sector == "Financials":
        return False
    return debt_to_equity_value is not None and debt_to_equity_value > 5


@dataclass(frozen=True)
class InterestCoverageResult:
    value: float | None
    label: str | None
    warning_flag: bool


def interest_coverage_ratio(
    operating_profit: float | int | None,
    other_income: float | int | None,
    interest: float | int | None,
) -> InterestCoverageResult:
    interest_value = _num(interest) or 0.0
    if interest_value == 0:
        return InterestCoverageResult(value=None, label="Debt Free", warning_flag=False)
    numerator = (_num(operating_profit) or 0.0) + (_num(other_income) or 0.0)
    value = numerator / interest_value
    return InterestCoverageResult(value=value, label=None, warning_flag=value < 1.5)


def net_debt(borrowings: float | int | None, investments: float | int | None) -> float:
    return (_num(borrowings) or 0.0) - (_num(investments) or 0.0)


def asset_turnover(sales: float | int | None, total_assets: float | int | None) -> float | None:
    sales_value = _num(sales)
    assets = _num(total_assets)
    if sales_value is None or assets in (None, 0):
        return None
    return sales_value / assets


def earnings_per_share(net_profit: float | int | None, equity_capital: float | int | None) -> float | None:
    profit = _num(net_profit)
    equity = _num(equity_capital)
    if profit is None or equity in (None, 0):
        return None
    return profit / equity


def book_value_per_share(
    equity_capital: float | int | None,
    reserves: float | int | None,
    face_value: float | int | None = 1,
) -> float | None:
    equity = _num(equity_capital)
    face = _num(face_value) or 1.0
    if equity in (None, 0):
        return None
    return (equity_base(equity_capital, reserves) or 0.0) / equity * face


def dividend_payout_ratio(dividend_payout: float | int | None) -> float | None:
    return _num(dividend_payout)
