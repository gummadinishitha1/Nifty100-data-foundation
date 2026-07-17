import pytest

from src.analytics.cagr import (
    BOTH_NEGATIVE,
    DECLINE_TO_LOSS,
    INSUFFICIENT,
    NORMAL,
    TURNAROUND,
    ZERO_BASE,
    calculate_cagr,
    fiscal_year_sort_key,
    windowed_cagr,
)


def test_normal_cagr():
    result = calculate_cagr(100, 121, 2)

    assert result.flag == NORMAL
    assert result.value == pytest.approx(10)


def test_turnaround_flag():
    result = calculate_cagr(-100, 50, 3)

    assert result.value is None
    assert result.flag == TURNAROUND


def test_decline_to_loss_flag():
    result = calculate_cagr(100, -50, 3)

    assert result.value is None
    assert result.flag == DECLINE_TO_LOSS


def test_both_negative_flag():
    result = calculate_cagr(-100, -50, 3)

    assert result.value is None
    assert result.flag == BOTH_NEGATIVE


def test_zero_base_flag():
    result = calculate_cagr(0, 50, 3)

    assert result.value is None
    assert result.flag == ZERO_BASE


def test_insufficient_for_missing_value():
    result = calculate_cagr(None, 50, 3)

    assert result.value is None
    assert result.flag == INSUFFICIENT


def test_windowed_cagr_insufficient_history():
    result = windowed_cagr([100, 110], 1, 3)

    assert result.value is None
    assert result.flag == INSUFFICIENT


def test_windowed_cagr_uses_start_offset():
    result = windowed_cagr([100, 110, 120, 133.1], 3, 3)

    assert result.flag == NORMAL
    assert result.value == pytest.approx(10, abs=0.01)


def test_fiscal_year_sort_key_orders_ttm_last():
    assert fiscal_year_sort_key("TTM") > fiscal_year_sort_key("Mar 2026")


def test_fiscal_year_sort_key_reads_year_label():
    assert fiscal_year_sort_key("Dec 2012") < fiscal_year_sort_key("Mar 2014")
