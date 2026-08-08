import pandas as pd
from src.screener.engine import add_composite_quality_score, apply_filters, run_screener


def test_de_filter_skips_financials_sector():
    df = pd.DataFrame(
        [
            {"company_id": "BANK", "broad_sector": "Financials", "debt_to_equity": 9.0, "composite_quality_score": 80},
            {"company_id": "AUTO", "broad_sector": "Automobile", "debt_to_equity": 0.8, "composite_quality_score": 70},
            {"company_id": "POWER", "broad_sector": "Energy", "debt_to_equity": 2.5, "composite_quality_score": 60},
        ]
    )

    result = apply_filters(df, {"de_max": 1.0})

    assert set(result["company_id"]) == {"BANK", "AUTO"}


def test_icr_filter_treats_debt_free_label_as_infinity():
    df = pd.DataFrame(
        [
            {"company_id": "DFREE", "interest_coverage": None, "icr_label": "Debt Free", "composite_quality_score": 90},
            {"company_id": "LOW", "interest_coverage": 1.5, "icr_label": None, "composite_quality_score": 80},
            {"company_id": "HIGH", "interest_coverage": 5.0, "icr_label": None, "composite_quality_score": 70},
        ]
    )

    result = apply_filters(df, {"icr_min": 3.0})

    assert result["company_id"].tolist() == ["DFREE", "HIGH"]


def test_add_composite_quality_score_when_missing():
    df = pd.DataFrame(
        [
            {
                "company_id": "A",
                "return_on_equity_pct": 20,
                "return_on_capital_employed_pct": 30,
                "cfo_quality_5yr": 1.1,
                "fcf_conversion_rate_pct": 40,
            }
        ]
    )

    result = add_composite_quality_score(df)

    assert result.loc[0, "composite_quality_score"] == 100


def test_run_screener_applies_custom_threshold_overrides(tmp_path):
    config_path = tmp_path / "screener_config.yaml"
    config_path.write_text(
        """
default_preset: test
presets:
  test:
    thresholds:
      roe_min: 10
""",
        encoding="utf-8",
    )
    df = pd.DataFrame(
        [
            {"company_id": "A", "roe": 12, "composite_quality_score": 50},
            {"company_id": "B", "roe": 8, "composite_quality_score": 60},
        ]
    )

    result = run_screener(
        financial_ratios=df,
        config_path=config_path,
        custom_thresholds={"roe_min": 9},
    )

    assert result["company_id"].tolist() == ["A"]
