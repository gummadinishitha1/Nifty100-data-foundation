from src.analytics.cashflow_kpis import (
    build_cashflow_intelligence,
    build_pattern_changes,
    capex_intensity,
    capex_label,
    capital_allocation_pattern,
    cfo_quality_label,
    cfo_quality_ratio,
    deleveraging_signal,
    distress_signal,
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


def test_distress_signal_requires_negative_cfo_and_positive_cff():
    assert distress_signal(-10, 40)
    assert not distress_signal(10, 40)


def test_deleveraging_signal_requires_negative_cff_and_declining_borrowings():
    assert deleveraging_signal(-20, 80, 100)
    assert not deleveraging_signal(-20, 120, 100)


def test_build_cashflow_intelligence_latest_company_metrics():
    base = __import__("pandas").DataFrame(
        [
            {
                "company_id": "ABC",
                "sector": "Industrials",
                "year": f"Mar {year}",
                "operating_activity": 100 + index * 10,
                "investing_activity": -20,
                "financing_activity": -10,
                "sales": 1000,
                "operating_profit": 100,
                "net_profit": 80,
                "borrowings": 100 - index * 5,
            }
            for index, year in enumerate(range(2019, 2025))
        ]
    )

    result = build_cashflow_intelligence(base)

    assert list(result.columns) == [
        "company_id",
        "sector",
        "cfo_quality_score",
        "cfo_quality_label",
        "capex_intensity_pct",
        "capex_label",
        "fcf_cagr_5yr",
        "fcf_conversion_pct",
        "distress_flag",
        "deleveraging_flag",
        "capital_allocation_label",
    ]
    assert result.loc[0, "company_id"] == "ABC"
    assert result.loc[0, "cfo_quality_label"] == "High Quality"
    assert result.loc[0, "capex_label"] == "Asset Light"
    assert result.loc[0, "deleveraging_flag"]


def test_build_pattern_changes_only_changed_latest_year():
    pd = __import__("pandas")
    capital = pd.DataFrame(
        [
            {"company_id": "ABC", "year": "Mar 2022", "pattern_label": "Reinvestor"},
            {"company_id": "ABC", "year": "Mar 2023", "pattern_label": "Reinvestor"},
            {"company_id": "ABC", "year": "Mar 2024", "pattern_label": "Distress Signal"},
            {"company_id": "XYZ", "year": "Mar 2023", "pattern_label": "Mixed"},
            {"company_id": "XYZ", "year": "Mar 2024", "pattern_label": "Mixed"},
        ]
    )
    sectors = pd.DataFrame([{"company_id": "ABC", "broad_sector": "Industrials"}])

    result = build_pattern_changes(capital, sectors)

    assert len(result) == 1
    assert result.loc[0, "change_text"] == "ABC moved from Reinvestor to Distress Signal"
