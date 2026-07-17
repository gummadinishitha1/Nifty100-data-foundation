from src.analytics.ratios import (
    asset_turnover,
    debt_to_equity,
    high_leverage_flag,
    interest_coverage_ratio,
    net_profit_margin,
    operating_profit_margin,
    return_on_assets,
    return_on_capital_employed,
    return_on_equity,
)


def test_net_profit_margin_normal_case():
    assert net_profit_margin(25, 100) == 25


def test_net_profit_margin_zero_sales_returns_none():
    assert net_profit_margin(25, 0) is None


def test_operating_profit_margin_cross_check_mismatch():
    result = operating_profit_margin(20, 100, 15)

    assert result.value == 20
    assert result.mismatch is True


def test_operating_profit_margin_cross_check_within_tolerance():
    result = operating_profit_margin(20, 100, 19.5)

    assert result.mismatch is False


def test_roe_negative_equity_returns_none():
    assert return_on_equity(100, 10, -20) is None


def test_roce_normal_case():
    assert round(return_on_capital_employed(30, 10, 40, 50), 2) == 30.0


def test_roa_zero_assets_returns_none():
    assert return_on_assets(100, 0) is None


def test_debt_to_equity_debt_free_returns_zero():
    assert debt_to_equity(0, 10, 90) == 0


def test_debt_to_equity_negative_equity_returns_none():
    assert debt_to_equity(10, 5, -10) is None


def test_high_debt_to_equity_flag_for_non_financials():
    assert high_leverage_flag(5.1, "Energy") is True


def test_high_debt_to_equity_suppressed_for_financials():
    assert high_leverage_flag(9.0, "Financials") is False


def test_interest_coverage_interest_zero_returns_none_and_label():
    result = interest_coverage_ratio(100, 10, 0)

    assert result.value is None
    assert result.label == "Debt Free"


def test_interest_coverage_warning_below_threshold():
    result = interest_coverage_ratio(100, 0, 100)

    assert result.value == 1
    assert result.warning_flag is True


def test_interest_coverage_no_warning_at_threshold():
    result = interest_coverage_ratio(150, 0, 100)

    assert result.value == 1.5
    assert result.warning_flag is False


def test_asset_turnover_zero_assets_returns_none():
    assert asset_turnover(100, 0) is None
