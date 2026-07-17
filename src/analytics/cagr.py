"""CAGR calculations with explicit edge-case flags."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
import re


NORMAL = "NORMAL"
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class CagrResult:
    value: float | None
    flag: str


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


def calculate_cagr(start: float | int | None, end: float | int | None, years: int) -> CagrResult:
    start_value = _num(start)
    end_value = _num(end)
    if start_value is None or end_value is None or years <= 0:
        return CagrResult(None, INSUFFICIENT)
    if start_value == 0:
        return CagrResult(None, ZERO_BASE)
    if start_value > 0 and end_value < 0:
        return CagrResult(None, DECLINE_TO_LOSS)
    if start_value < 0 and end_value > 0:
        return CagrResult(None, TURNAROUND)
    if start_value < 0 and end_value < 0:
        return CagrResult(None, BOTH_NEGATIVE)
    if start_value < 0 or end_value < 0:
        return CagrResult(None, BOTH_NEGATIVE)
    return CagrResult(((end_value / start_value) ** (1 / years) - 1) * 100, NORMAL)


def fiscal_year_sort_key(year_label: object) -> tuple[int, int, str]:
    label = "" if year_label is None else str(year_label)
    if label.strip().upper() == "TTM":
        return (9999, 12, label)
    match = re.search(r"(\d{4})", label)
    year = int(match.group(1)) if match else 0
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
    month = month_order.get(label[:3].upper(), 0)
    return (year, month, label)


def windowed_cagr(values: list[float | int | None], end_index: int, years: int) -> CagrResult:
    start_index = end_index - years
    if start_index < 0:
        return CagrResult(None, INSUFFICIENT)
    return calculate_cagr(values[start_index], values[end_index], years)
