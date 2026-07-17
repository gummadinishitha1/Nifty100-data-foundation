from src.analytics.cashflow_kpis import (
    capex_intensity,
    capex_label,
    capital_allocation_pattern,
    cfo_quality_label,
    cfo_quality_ratio,
    fcf_conversion_rate,
    free_cash_flow,
)


def test_free_cash_flow_allows_negative_value():
    assert free_cash_flow(100, -140) == -40


def test_cfo_quality_ratio_pat_zero_returns_none():
    assert cfo_quality_ratio(100, 0) is None


def test_cfo_quality_label_high_quality():
    assert cfo_quality_label(1.2) == "High Quality"


def test_capex_intensity_uses_absolute_investing_activity():
    assert capex_intensity(-8, 100) == 8


def test_capex_label_capital_intensive():
    assert capex_label(8.1) == "Capital Intensive"


def test_fcf_conversion_zero_operating_profit_returns_none():
    assert fcf_conversion_rate(50, 0) is None


def test_capital_allocation_reinvestor():
    assert capital_allocation_pattern(100, -40, -20, 0.8) == "Reinvestor"


def test_capital_allocation_shareholder_returns():
    assert capital_allocation_pattern(100, -40, -20, 1.2) == "Shareholder Returns"


def test_capital_allocation_distress_signal():
    assert capital_allocation_pattern(-10, 30, 40) == "Distress Signal"


def test_capital_allocation_growth_funded_by_debt():
    assert capital_allocation_pattern(-10, -30, 40) == "Growth Funded by Debt"
