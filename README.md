# Nifty100 Data Foundation

This project builds the data foundation for the Nifty100 analytics workflow by loading Excel source files into a SQLite database, validating the loaded data, and producing reusable output artifacts.

## What is included

- ETL helpers for loading and normalizing Excel-based financial data
- SQLite schema and database initialization logic
- Data quality validation pipeline with generated reports
- Unit tests covering the ETL and normalization logic
- Exploratory SQL queries for downstream analysis

## Project structure

- src/etl/loader.py - Excel loading and basic cleaning
- src/etl/normaliser.py - value normalization helpers
- src/etl/validator.py - data quality validation functions
- src/load_database.py - end-to-end loading into SQLite
- src/database.py - database schema initialization
- src/database_validator.py - database-level validation and report generation
- db/schema.sql - SQLite schema for the core tables
- output/ - generated load and validation reports
- tests/etl/ - ETL unit tests
- notebooks/exploratory_queries.sql - starter exploratory SQL

## Main commands

Run the ETL load:

```bash
python src/load_database.py
```

Expected output:

```text
Loaded companies: 92 rows
Loaded profitandloss: 1263 rows
Loaded balancesheet: 1225 rows
Loaded cashflow: 1164 rows
Loaded stock_prices: 5520 rows
Load completed successfully!
```

Generate validation reports:

```bash
python src/database_validator.py
```

Expected output:

```text
Validation completed successfully!
```

Run the test suite:

```bash
pytest -q
```

Expected output:

```text
32 passed
```

## Current sprint deliverables

The project currently produces:

- SQLite database at data/db/nifty100.db
- Load audit report at output/load_audit.csv
- Validation failure report at output/validation_failures.csv
- Validation summary at output/database_validation_report.csv

## Verified results

The current database build has been verified with:

- 12 tables created
- 92 companies loaded
- 1263 profit and loss rows loaded
- 1225 balance sheet rows loaded
- 1164 cash flow rows loaded
- 5520 stock price rows loaded
- 0 foreign key violations

## Notes

The project is set up for Sprint 1 data foundation work and is ready for the next analytics module development.
