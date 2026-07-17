# Sprint 2 Formula Decisions

## Ratio Denominators

- Net profit margin returns `None` when sales is zero.
- ROE uses `net_profit / (equity_capital + reserves) * 100` and returns `None` when equity plus reserves is zero or negative.
- ROCE uses `(operating_profit + other_income) / (equity_capital + reserves + borrowings) * 100`.
- ROA and asset turnover return `None` when total assets is zero.

## Financials Carve-Out

- Companies in the `Financials` broad sector keep computed ROCE values, but the benchmark type is stored as `sector_relative`.
- The high debt-to-equity warning is suppressed for `Financials`, because structural leverage is normal for banks, NBFCs, and insurers.

## Leverage And Interest Coverage

- Debt-to-equity returns `0` for debt-free companies.
- Interest coverage returns `None` when interest is zero and stores the display label `Debt Free`.
- Interest coverage below `1.5` sets `icr_warning_flag`.

## CAGR Edge Cases

- Positive base and positive end values compute normally.
- Positive to negative returns `None` with `DECLINE_TO_LOSS`.
- Negative to positive returns `None` with `TURNAROUND`.
- Negative to negative returns `None` with `BOTH_NEGATIVE`.
- Zero base returns `None` with `ZERO_BASE`.
- Missing lookback history returns `None` with `INSUFFICIENT`.

## Cash Flow KPIs

- Free cash flow is `operating_activity + investing_activity`; negative values are retained.
- CFO quality is a rolling five-period average of `CFO / PAT`; PAT of zero is excluded from the average.
- CapEx intensity uses `abs(investing_activity) / sales * 100`.
- Capital allocation labels are assigned from the signs of CFO, CFI, and CFF, with `(+,-,-)` promoted to `Shareholder Returns` when CFO/PAT is above `1.0`.

## Source Cross-Checks

- OPM differences above one percentage point are logged as formula discrepancies.
- ROCE differences above five percentage points versus the company-level source display value are logged and categorized.
- ROE differences above five percentage points are logged, but computed ROE remains the analytics value and the source value is treated as display-only.
