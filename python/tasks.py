"""
DekaBank Interview Prep - Python Tasks
=======================================
Five practical tasks covering ETL, data quality, reporting,
financial calculations, and incremental loading patterns.

Complete each TODO block. Check solutions.py when done.

Setup:
    pip install pandas sqlalchemy psycopg2-binary numpy
    Make sure Docker PostgreSQL is running and data is loaded.
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import date, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional

DB_URL = "postgresql://postgres:password@localhost:5432/postgres"


# ==============================================================
# TASK A: Data Quality Framework
# ==============================================================
# Build a reusable DQ check framework that validates the
# transactions DataFrame loaded from PostgreSQL.
#
# Requirements:
#   1. Check: no NULL values in critical columns
#      (transaction_id, fund_id, amount_eur, transaction_date)
#   2. Check: all amount_eur values are positive
#   3. Check: no future transaction dates
#   4. Check: settlement_date >= transaction_date
#   5. Print a summary report: PASSED / FAILED per check + row count
# ==============================================================

@dataclass
class DQResult:
    check_name: str
    passed:     bool
    failed_rows: int
    details:    str


def run_dq_checks(df: pd.DataFrame) -> List[DQResult]:
    """
    TODO: Implement all 5 data quality checks.
    Return a list of DQResult objects, one per check.
    """
    results = []
    # TODO: Implement each check here
    raise NotImplementedError("Task A: implement run_dq_checks()")
    return results


def print_dq_report(results: List[DQResult]) -> None:
    """TODO: Print a formatted DQ report to stdout."""
    raise NotImplementedError("Task A: implement print_dq_report()")


# ==============================================================
# TASK B: NAV ETL Loader
# ==============================================================
# Load fund NAV data from a CSV file, validate it, transform it,
# and upsert it into the fund_nav table in PostgreSQL.
#
# Requirements:
#   1. Read the CSV from ../data/fund_nav.csv
#   2. Validate: no nulls, nav_price > 0, valid fund_ids (1-10)
#   3. Transform: add a 'loaded_at' timestamp column
#   4. Upsert: insert rows, skip duplicates (fund_id + nav_date)
#   5. Return count of rows inserted vs skipped
# ==============================================================

def load_nav_from_csv(csv_path: str, engine) -> Dict[str, int]:
    """
    TODO: Implement the NAV ETL loader.
    Returns: {'inserted': N, 'skipped': M}
    """
    raise NotImplementedError("Task B: implement load_nav_from_csv()")


# ==============================================================
# TASK C: AuM Report Generator
# ==============================================================
# Generate a monthly Assets-under-Management report per Sparkasse.
#
# Requirements:
#   1. Query holdings * latest NAV per depot
#   2. Aggregate total AuM per Sparkasse
#   3. Calculate month-over-month AuM change (%)
#   4. Return a sorted DataFrame (highest AuM first)
#   5. Export to CSV at ../data/aum_report.csv
#
# Expected columns:
#   sparkasse_name, region, total_aum_eur, depot_count,
#   customer_count, mom_change_pct
# ==============================================================

def generate_aum_report(engine) -> pd.DataFrame:
    """
    TODO: Implement the AuM report generator.
    """
    raise NotImplementedError("Task C: implement generate_aum_report()")


# ==============================================================
# TASK D: Fund Return Calculator
# ==============================================================
# Calculate Time-Weighted Rate of Return (TWRR) for a given
# fund over a specified date range.
#
# Requirements:
#   1. Load NAV prices for fund_id between start_date and end_date
#   2. Calculate daily sub-period returns: r = (P_t / P_t-1) - 1
#   3. Chain them: TWRR = product(1 + r_i) - 1
#   4. Also compute annualised return: (1 + TWRR)^(365/days) - 1
#   5. Return dict with keys: twrr, annualised_return, start_nav,
#      end_nav, trading_days
# ==============================================================

def calculate_fund_twrr(
    fund_id: int,
    start_date: date,
    end_date: date,
    engine
) -> Dict[str, float]:
    """
    TODO: Implement TWRR calculation.
    """
    raise NotImplementedError("Task D: implement calculate_fund_twrr()")


# ==============================================================
# TASK E: Incremental Watermark Load
# ==============================================================
# Simulate an incremental ETL pipeline that only loads new
# transactions since the last run (watermark pattern).
#
# Requirements:
#   1. Read the watermark from a file (watermark.txt) if it exists
#      Default to 30 days ago if no watermark exists.
#   2. Query only transactions after the watermark date
#   3. Process them: add 'net_flow' column
#      (positive for BUY/SWITCH_IN, negative for SELL/SWITCH_OUT)
#   4. Save the processed batch to ../data/incremental_batch.csv
#   5. Update watermark.txt with today's date
#   6. Return count of records processed
# ==============================================================

WATERMARK_FILE = "watermark.txt"


def run_incremental_load(engine) -> int:
    """
    TODO: Implement the incremental watermark-based ETL.
    Returns: number of records processed
    """
    raise NotImplementedError("Task E: implement run_incremental_load()")


# ==============================================================
# RUNNER - executes all tasks
# ==============================================================
if __name__ == '__main__':
    import os
    engine = create_engine(DB_URL)

    print("\n" + "=" * 55)
    print(" TASK A: Data Quality Framework")
    print("=" * 55)
    with engine.connect() as conn:
        df_txn = pd.read_sql(
            "SELECT * FROM deka.transactions LIMIT 5000", conn
        )
    results = run_dq_checks(df_txn)
    print_dq_report(results)

    print("\n" + "=" * 55)
    print(" TASK B: NAV ETL Loader")
    print("=" * 55)
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fund_nav.csv')
    stats = load_nav_from_csv(csv_path, engine)
    print(f"  Inserted: {stats.get('inserted', 0)}, Skipped: {stats.get('skipped', 0)}")

    print("\n" + "=" * 55)
    print(" TASK C: AuM Report Generator")
    print("=" * 55)
    df_aum = generate_aum_report(engine)
    print(df_aum.head(10).to_string(index=False))

    print("\n" + "=" * 55)
    print(" TASK D: Fund Return Calculator (fund_id=1, last year)")
    print("=" * 55)
    result = calculate_fund_twrr(
        fund_id=1,
        start_date=date.today() - timedelta(days=365),
        end_date=date.today(),
        engine=engine
    )
    for k, v in result.items():
        print(f"  {k}: {v}")

    print("\n" + "=" * 55)
    print(" TASK E: Incremental Watermark Load")
    print("=" * 55)
    n = run_incremental_load(engine)
    print(f"  Processed {n} new records")
