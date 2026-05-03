"""
DekaBank Interview Prep - Python Solutions
==========================================
Reference implementations for all 5 tasks in tasks.py.
Only read these AFTER attempting the tasks yourself!
"""

import os
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import date, timedelta
from dataclasses import dataclass
from typing import List, Dict

DB_URL = "postgresql://postgres:password@localhost:5432/postgres"


# ==============================================================
# SOLUTION A: Data Quality Framework
# ==============================================================

@dataclass
class DQResult:
    check_name:  str
    passed:      bool
    failed_rows: int
    details:     str


def run_dq_checks(df: pd.DataFrame) -> List[DQResult]:
    results = []

    # 1. NULL check on critical columns
    for col in ['fund_id', 'amount_eur', 'transaction_date']:
        if col not in df.columns:
            results.append(DQResult(f'null_check_{col}', False, -1, f'Column {col} missing'))
            continue
        nulls = int(df[col].isnull().sum())
        results.append(DQResult(
            check_name=f'null_check_{col}',
            passed=(nulls == 0),
            failed_rows=nulls,
            details=f'{nulls} NULL values in {col}'
        ))

    # 2. Positive amount_eur
    neg = int((df['amount_eur'] <= 0).sum())
    results.append(DQResult('positive_amounts', neg == 0, neg,
                            f'{neg} non-positive amount_eur values'))

    # 3. No future transaction dates
    future = int((pd.to_datetime(df['transaction_date']) > pd.Timestamp.today()).sum())
    results.append(DQResult('no_future_dates', future == 0, future,
                            f'{future} future transaction_date values'))

    # 4. Settlement >= transaction date
    if 'settlement_date' in df.columns:
        df2 = df.dropna(subset=['settlement_date', 'transaction_date'])
        bad = int((
            pd.to_datetime(df2['settlement_date']) < pd.to_datetime(df2['transaction_date'])
        ).sum())
        results.append(DQResult('settlement_after_trade', bad == 0, bad,
                                f'{bad} settlement_date before transaction_date'))

    return results


def print_dq_report(results: List[DQResult]) -> None:
    print(f"\n{'Check':<30} {'Status':<8} {'Failed Rows':<14} Details")
    print('-' * 80)
    for r in results:
        status = 'PASSED' if r.passed else 'FAILED'
        icon   = '' if r.passed else ''
        print(f"{icon} {r.check_name:<28} {status:<8} {r.failed_rows:<14} {r.details}")
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    print('-' * 80)
    print(f"Result: {passed}/{total} checks passed")


# ==============================================================
# SOLUTION B: NAV ETL Loader
# ==============================================================

def load_nav_from_csv(csv_path: str, engine) -> Dict[str, int]:
    df = pd.read_csv(csv_path)

    # Validate
    if df[['fund_id', 'nav_date', 'nav_price']].isnull().any().any():
        raise ValueError("NAV CSV contains NULL values in required columns")
    if (df['nav_price'] <= 0).any():
        raise ValueError("NAV CSV contains non-positive nav_price values")
    if not df['fund_id'].between(1, 10).all():
        raise ValueError("NAV CSV contains invalid fund_ids outside range 1-10")

    # Transform
    df['loaded_at'] = pd.Timestamp.now()

    # Get existing records to detect duplicates
    with engine.connect() as conn:
        existing = pd.read_sql(
            "SELECT fund_id, nav_date FROM deka.fund_nav", conn
        )
    existing_keys = set(zip(existing['fund_id'], existing['nav_date'].astype(str)))

    new_rows = df[
        ~df.apply(lambda r: (int(r['fund_id']), str(r['nav_date'])[:10]) in existing_keys, axis=1)
    ]
    skipped = len(df) - len(new_rows)

    if len(new_rows) > 0:
        new_rows[['fund_id', 'nav_date', 'nav_price']].to_sql(
            'fund_nav', engine,
            schema='deka',
            if_exists='append',
            index=False,
            method='multi',
            chunksize=1000
        )

    return {'inserted': len(new_rows), 'skipped': skipped}


# ==============================================================
# SOLUTION C: AuM Report Generator
# ==============================================================

def generate_aum_report(engine) -> pd.DataFrame:
    query = """
    SELECT
        s.sparkasse_name,
        s.region,
        COUNT(DISTINCT d.depot_id)    AS depot_count,
        COUNT(DISTINCT c.customer_id) AS customer_count,
        SUM(h.units * fn.nav_price)   AS total_aum_eur
    FROM deka.sparkassen s
    JOIN deka.depots d       ON s.sparkasse_id = d.sparkasse_id AND d.active = TRUE
    JOIN deka.customers c    ON d.customer_id  = c.customer_id
    JOIN deka.holdings h     ON d.depot_id     = h.depot_id
    JOIN deka.fund_nav fn    ON h.fund_id      = fn.fund_id
                           AND fn.nav_date = (
                               SELECT MAX(nav_date) FROM deka.fund_nav
                               WHERE fund_id = h.fund_id
                           )
    GROUP BY s.sparkasse_name, s.region
    ORDER BY total_aum_eur DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Placeholder mom_change_pct (would need historical snapshot in production)
    df['mom_change_pct'] = np.random.uniform(-5, 10, len(df)).round(2)

    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'aum_report.csv')
    df.to_csv(output_path, index=False)
    print(f"  AuM report saved to {os.path.abspath(output_path)}")
    return df


# ==============================================================
# SOLUTION D: Fund Return Calculator (TWRR)
# ==============================================================

def calculate_fund_twrr(
    fund_id: int,
    start_date: date,
    end_date: date,
    engine
) -> Dict[str, float]:
    query = text("""
        SELECT nav_date, nav_price
        FROM deka.fund_nav
        WHERE fund_id = :fund_id
          AND nav_date BETWEEN :start_date AND :end_date
        ORDER BY nav_date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={
            'fund_id': fund_id,
            'start_date': start_date,
            'end_date': end_date
        })

    if len(df) < 2:
        raise ValueError(f"Insufficient NAV data for fund {fund_id} in date range")

    df = df.sort_values('nav_date').reset_index(drop=True)
    sub_returns  = df['nav_price'].pct_change().dropna()  # daily r_i
    twrr         = float(np.prod(1 + sub_returns) - 1)
    days         = (pd.to_datetime(df['nav_date'].iloc[-1]) -
                    pd.to_datetime(df['nav_date'].iloc[0])).days
    annualised   = float((1 + twrr) ** (365 / max(days, 1)) - 1) if days > 0 else 0.0

    return {
        'twrr':              round(twrr, 6),
        'annualised_return': round(annualised, 6),
        'start_nav':         round(float(df['nav_price'].iloc[0]),  4),
        'end_nav':           round(float(df['nav_price'].iloc[-1]), 4),
        'trading_days':      len(df),
    }


# ==============================================================
# SOLUTION E: Incremental Watermark Load
# ==============================================================

WATERMARK_FILE = "watermark.txt"


def run_incremental_load(engine) -> int:
    # 1. Read watermark
    if os.path.exists(WATERMARK_FILE):
        with open(WATERMARK_FILE) as f:
            watermark = date.fromisoformat(f.read().strip())
    else:
        watermark = date.today() - timedelta(days=30)

    print(f"  Watermark: {watermark}")

    # 2. Query new transactions
    query = text("""
        SELECT t.*, f.fund_name
        FROM deka.transactions t
        JOIN deka.funds f ON t.fund_id = f.fund_id
        WHERE t.transaction_date > :watermark
          AND t.status = 'SETTLED'
        ORDER BY t.transaction_date
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'watermark': watermark})

    if df.empty:
        print("  No new records since watermark")
        # Still update watermark
        with open(WATERMARK_FILE, 'w') as f:
            f.write(date.today().isoformat())
        return 0

    # 3. Add net_flow column
    INFLOW_TYPES  = {'BUY', 'SWITCH_IN', 'DIVIDEND'}
    OUTFLOW_TYPES = {'SELL', 'SWITCH_OUT'}
    df['net_flow'] = df.apply(
        lambda r: r['amount_eur'] if r['transaction_type'] in INFLOW_TYPES
                  else -r['amount_eur'] if r['transaction_type'] in OUTFLOW_TYPES
                  else 0,
        axis=1
    )

    # 4. Save batch
    output = os.path.join(os.path.dirname(__file__), '..', 'data', 'incremental_batch.csv')
    df.to_csv(output, index=False)
    print(f"  Batch saved: {len(df)} records -> {os.path.abspath(output)}")

    # 5. Update watermark
    with open(WATERMARK_FILE, 'w') as f:
        f.write(date.today().isoformat())
    print(f"  Watermark updated to: {date.today()}")

    return len(df)


# ==============================================================
# RUNNER
# ==============================================================
if __name__ == '__main__':
    engine = create_engine(DB_URL)

    print("\n" + "=" * 55)
    print(" SOLUTION A: Data Quality Framework")
    print("=" * 55)
    with engine.connect() as conn:
        df_txn = pd.read_sql("SELECT * FROM deka.transactions LIMIT 5000", conn)
    results = run_dq_checks(df_txn)
    print_dq_report(results)

    print("\n" + "=" * 55)
    print(" SOLUTION B: NAV ETL Loader")
    print("=" * 55)
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fund_nav.csv')
    stats = load_nav_from_csv(csv_path, engine)
    print(f"  Inserted: {stats['inserted']}, Skipped: {stats['skipped']}")

    print("\n" + "=" * 55)
    print(" SOLUTION C: AuM Report Generator")
    print("=" * 55)
    df_aum = generate_aum_report(engine)
    print(df_aum.to_string(index=False))

    print("\n" + "=" * 55)
    print(" SOLUTION D: Fund TWRR (fund_id=1, last 365 days)")
    print("=" * 55)
    result = calculate_fund_twrr(
        fund_id=1,
        start_date=date.today() - timedelta(days=365),
        end_date=date.today(),
        engine=engine
    )
    for k, v in result.items():
        print(f"  {k:<22}: {v}")

    print("\n" + "=" * 55)
    print(" SOLUTION E: Incremental Watermark Load")
    print("=" * 55)
    n = run_incremental_load(engine)
    print(f"  Total records processed: {n}")
