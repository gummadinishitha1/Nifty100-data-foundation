from pathlib import Path

import pandas as pd

from src.analytics.peer import compute_peer_percentiles, peer_group_message


def test_debt_to_equity_percentile_is_inverse():
    df = pd.DataFrame(
        [
            {"company_id": "LOW", "peer_group_name": "Test", "debt_to_equity": 0.1, "year": "Mar 2024"},
            {"company_id": "MID", "peer_group_name": "Test", "debt_to_equity": 0.5, "year": "Mar 2024"},
            {"company_id": "HIGH", "peer_group_name": "Test", "debt_to_equity": 1.0, "year": "Mar 2024"},
        ]
    )

    result = compute_peer_percentiles(df)
    de = result[result["metric"].eq("D/E")].set_index("company_id")["percentile_rank"]

    assert de["LOW"] == 1.0
    assert de["MID"] == 0.5
    assert de["HIGH"] == 0.0


def test_highest_roe_gets_highest_percentile():
    df = pd.DataFrame(
        [
            {"company_id": "A", "peer_group_name": "IT Services", "return_on_equity_pct": 10, "year": "Mar 2024"},
            {"company_id": "B", "peer_group_name": "IT Services", "return_on_equity_pct": 20, "year": "Mar 2024"},
            {"company_id": "C", "peer_group_name": "IT Services", "return_on_equity_pct": 30, "year": "Mar 2024"},
        ]
    )

    result = compute_peer_percentiles(df)
    roe = result[result["metric"].eq("ROE")].set_index("company_id")["percentile_rank"]

    assert roe["C"] == 1.0
    assert roe["B"] == 0.5
    assert roe["A"] == 0.0


def test_company_without_peer_group_returns_message():
    config_dir = Path(".pytest_tmp_local")
    config_dir.mkdir(exist_ok=True)
    path = config_dir / "peer_groups_message.xlsx"
    pd.DataFrame(
        [{"peer_group_name": "Test", "company_id": "ABC", "is_benchmark": True}]
    ).to_excel(path, index=False)

    assert peer_group_message("XYZ", path) == "No peer group assigned"
