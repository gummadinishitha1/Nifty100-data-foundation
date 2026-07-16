PRAGMA foreign_keys = ON;

-- ==========================
-- Companies Master
-- ==========================

CREATE TABLE companies (
    id TEXT PRIMARY KEY,
    company_logo TEXT,
    company_name TEXT,
    chart_link TEXT,
    about_company TEXT,
    website TEXT,
    nse_profile TEXT,
    bse_profile TEXT,
    face_value REAL,
    book_value REAL,
    roce_percentage REAL,
    roe_percentage REAL
);


-- ==========================
-- Profit & Loss
-- ==========================

CREATE TABLE IF NOT EXISTS profitandloss (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    year INTEGER NOT NULL,
    sales REAL,
    expenses REAL,
    operating_profit REAL,
    opm_percentage REAL,
    other_income REAL,
    interest REAL,
    depreciation REAL,
    profit_before_tax REAL,
    tax_percentage REAL,
    net_profit REAL,
    eps REAL,
    dividend_payout REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Balance Sheet
-- ==========================

CREATE TABLE IF NOT EXISTS balancesheet (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    year INTEGER NOT NULL,
    equity_capital REAL,
    reserves REAL,
    borrowings REAL,
    other_liabilities REAL,
    total_liabilities REAL,
    fixed_assets REAL,
    cwip REAL,
    investments REAL,
    other_asset REAL,
    total_assets REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Cash Flow
-- ==========================

CREATE TABLE cashflow (
    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT,
    operating_activity REAL,
    investing_activity REAL,
    financing_activity REAL,
    net_cash_flow REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Company Analysis
-- ==========================

CREATE TABLE IF NOT EXISTS analysis (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    compounded_sales_growth REAL,
    compounded_profit_growth REAL,
    stock_price_cagr REAL,
    roe REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Documents
-- ==========================

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    Year INTEGER,
    Annual_Report TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Financial Ratios
-- ==========================

CREATE TABLE financial_ratios (

    id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    year TEXT,

    pe_ratio REAL,
    pb_ratio REAL,
    dividend_yield REAL,
    roe REAL,
    roce REAL,
    debt_to_equity REAL,
    interest_coverage REAL,
    sales_growth REAL,
    profit_growth REAL,
    eps_growth REAL,
    opm REAL,
    npm REAL,
    other_ratio REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Market Cap
-- ==========================

CREATE TABLE IF NOT EXISTS market_cap (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    year INTEGER,
    market_cap_crore REAL,
    enterprise_value_crore REAL,
    pe_ratio REAL,
    pb_ratio REAL,
    ev_ebitda REAL,
    dividend_yield_pct REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Peer Groups
-- ==========================

CREATE TABLE IF NOT EXISTS peer_groups (
    id TEXT PRIMARY KEY,
    peer_group_name TEXT,
    company_id TEXT,
    is_benchmark INTEGER,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Sectors
-- ==========================

CREATE TABLE IF NOT EXISTS sectors (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    broad_sector TEXT,
    sub_sector TEXT,
    index_weight_pct REAL,
    market_cap_category TEXT,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);


-- ==========================
-- Stock Prices
-- ==========================

CREATE TABLE IF NOT EXISTS stock_prices (
    id TEXT PRIMARY KEY,
    company_id TEXT,
    date TEXT,
    open_price REAL,
    high_price REAL,
    low_price REAL,
    close_price REAL,
    volume INTEGER,
    adjusted_close REAL,

    FOREIGN KEY(company_id)
        REFERENCES companies(id)
);