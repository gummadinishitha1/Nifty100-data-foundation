-- Sprint 1 exploratory queries
-- 1. Company master overview
SELECT id, company_name, website FROM companies ORDER BY company_name LIMIT 20;

-- 2. Top companies by revenue
SELECT company_id, year, sales FROM profitandloss ORDER BY sales DESC LIMIT 20;

-- 3. Companies with the highest operating profit margin
SELECT company_id, year, opm_percentage
FROM profitandloss
WHERE opm_percentage IS NOT NULL
ORDER BY opm_percentage DESC
LIMIT 20;

-- 4. Balance sheet health check
SELECT company_id, year, total_assets, total_liabilities
FROM balancesheet
ORDER BY total_assets DESC
LIMIT 20;

-- 5. Cash flow summary
SELECT company_id, year, operating_activity, investing_activity, financing_activity, net_cash_flow
FROM cashflow
ORDER BY net_cash_flow DESC
LIMIT 20;

-- 6. Dividend yield snapshot
SELECT company_id, year, dividend_yield
FROM financial_ratios
WHERE dividend_yield IS NOT NULL
ORDER BY dividend_yield DESC
LIMIT 20;

-- 7. Sector distribution
SELECT broad_sector, sub_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector, sub_sector
ORDER BY company_count DESC;

-- 8. Latest stock price trend
SELECT company_id, date, close_price
FROM stock_prices
WHERE company_id = 'TCS'
ORDER BY date DESC
LIMIT 10;

-- 9. Companies with missing annual report links
SELECT company_id, Year
FROM documents
WHERE Annual_Report IS NULL OR TRIM(Annual_Report) = '';

-- 10. Duplicate company-year audit
SELECT company_id, year, COUNT(*) AS row_count
FROM profitandloss
GROUP BY company_id, year
HAVING COUNT(*) > 1;
