# DekaBank Interview Prep

**DekaBank Azure Cloud Developer — Technical Interview Practice Kit**

SQL + Python ETL exercises on realistic bank data: Sparkassen, funds, depots, NAV prices, and transactions — all modelled after DekaBank's actual Wertpapierhaus business.

---

## Repository Structure

```
dekabank-interview-prep/
├── sql/
│   ├── 01_schema.sql        # PostgreSQL schema: 7 tables + 2 views
│   ├── 02_seed_data.sql     # 10 Sparkassen + 10 DekaBank-style funds
│   ├── 03_exercises.sql     # 10 SQL exercises (easy → hard)
│   └── 04_solutions.sql    # Reference solutions for all 10 exercises
├── python/
│   ├── generate_data.py     # Synthetic data generator (run this first!)
│   ├── tasks.py             # 5 Python tasks with TODO stubs
│   └── solutions.py        # Full reference solutions
└── data/                    # Generated CSV files (git-ignored)
    ├── customers.csv
    ├── depots.csv
    ├── fund_nav.csv
    ├── holdings.csv
    └── transactions.csv
```

---

## Quick Start (5 steps)

### Step 1 — Clone the repository

```bash
git clone https://github.com/wang-yuhao/dekabank-interview-prep.git
cd dekabank-interview-prep
```

### Step 2 — Start PostgreSQL with Docker

```bash
docker run --name deka-db \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 -d postgres:15
```

### Step 3 — Generate synthetic CSV data

```bash
pip install pandas numpy sqlalchemy psycopg2-binary
python python/generate_data.py
```

This creates ~10,000+ rows of realistic bank data with intentional DQ errors injected.

### Step 4 — Load the schema and seed data

```bash
# Create schema (7 tables + 2 views)
docker exec -i deka-db psql -U postgres < sql/01_schema.sql

# Insert reference data (Sparkassen + Funds)
docker exec -i deka-db psql -U postgres < sql/02_seed_data.sql

# Copy CSVs into Docker container
docker cp data/ deka-db:/data/
```

### Step 5 — Load CSV data into PostgreSQL

```bash
docker exec -it deka-db psql -U postgres
```

Then inside psql:

```sql
SET search_path TO deka;

\copy deka.customers(customer_code,sparkasse_id,first_name,last_name,date_of_birth,customer_since,risk_profile)
  FROM '/data/customers.csv' CSV HEADER;

\copy deka.depots(depot_number,customer_id,sparkasse_id,depot_type,opened_date)
  FROM '/data/depots.csv' CSV HEADER;

\copy deka.fund_nav(fund_id,nav_date,nav_price)
  FROM '/data/fund_nav.csv' CSV HEADER;

\copy deka.holdings(depot_id,fund_id,units,avg_purchase_price)
  FROM '/data/holdings.csv' CSV HEADER;

\copy deka.transactions(depot_id,fund_id,transaction_date,settlement_date,transaction_type,units,nav_price,amount_eur,fee_eur,status)
  FROM '/data/transactions.csv' CSV HEADER;
```

---

## Database Schema

| Table | Rows | Description |
|---|---|---|
| `sparkassen` | 10 | German savings bank branches |
| `funds` | 10 | Investment funds with ISIN |
| `customers` | ~500 | Investors with risk profiles |
| `depots` | ~700 | Custody accounts |
| `fund_nav` | ~6,000 | Daily NAV prices (2023–2025) |
| `holdings` | ~2,000 | Current fund positions |
| `transactions` | ~10,000 | Buy/sell history + DQ errors |

**Business hierarchy:** `Sparkasse → Depot → Customer → Transaction → Fund`

---

## SQL Exercises Overview

| # | Difficulty | Topic |
|---|---|---|
| 1 | Easy | Fund listing with TER sort |
| 2 | Easy | Customer count by risk profile |
| 3 | Easy | Transaction volume last 90 days |
| 4 | Medium | Top Sparkassen by net inflow (30d) |
| 5 | Medium | Month-over-month NAV change (LAG) |
| 6 | Medium | Customer AuM tier classification |
| 7 | Medium | Dormant depot detection |
| 8 | Hard | Data quality multi-check |
| 9 | Hard | Cumulative net inflow (running total) |
| 10 | Hard | Sparkasse performance ranking (RANK) |

**Rule:** Attempt `03_exercises.sql` BEFORE opening `04_solutions.sql`.

---

## Python Tasks Overview

| Task | Topic | Key Skills |
|---|---|---|
| A | Data Quality Framework | Pandas, assertions, reporting |
| B | NAV ETL Loader | CSV ingestion, upsert logic |
| C | AuM Report Generator | SQL + pandas aggregation |
| D | Fund TWRR Calculator | Financial math, NumPy |
| E | Incremental Watermark Load | ETL patterns, state management |

**Rule:** Implement TODOs in `tasks.py` BEFORE reading `solutions.py`.

---

## Connecting with DBeaver / DataGrip

| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `postgres` |
| User | `postgres` |
| Password | `password` |
| Schema | `deka` |

---

## Key Business Concepts

- **AuM** (Assets under Management) = `units × latest NAV price`
- **Net inflow** = BUY amount − SELL amount per Sparkasse
- **T+2 settlement**: fund transactions must settle within 2 business days
- **NAV** (Net Asset Value): fund price published at end of each trading day
- **TER** (Total Expense Ratio): annual fund management fee
- **ISIN**: 12-character international securities identifier

---

## Daily Git Workflow

```bash
# Start of session — pull latest
git pull origin main

# After working on exercises
git add sql/03_exercises.sql
git commit -m "practice: complete SQL exercises 1-5"
git push origin main

# Create a branch for a clean attempt
git checkout -b exercises/attempt-2
```

---

## Tech Stack

- **Database**: PostgreSQL 15 (Docker)
- **Python**: pandas, NumPy, SQLAlchemy, psycopg2
- **Concepts covered**: Window functions, CTEs, incremental ETL, data quality, financial calculations, Azure data patterns

---

*Interview prep for DekaBank Azure Cloud Developer role — modelled on their Databricks/PySpark/Oracle/Informatica stack and Sparkassen sales reporting domain.*
