"""
DekaBank Interview Prep - Synthetic Data Generator
====================================================
Generates realistic CSV files for all database tables.
Run this script once, then load the CSVs into PostgreSQL.

Usage:
    python generate_data.py

Outputs (in ../data/ directory):
    customers.csv, depots.csv, fund_nav.csv, holdings.csv, transactions.csv
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import date, timedelta

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- Constants aligned with seed data ----
NUM_SPARKASSEN = 10
NUM_FUNDS      = 10
NUM_CUSTOMERS  = 500
NAV_START      = date(2023, 1, 2)
NAV_END        = date(2025, 5, 2)

RISK_PROFILES = ['CONSERVATIVE', 'BALANCED', 'GROWTH', 'AGGRESSIVE']
DEPOT_TYPES   = ['STANDARD', 'VL', 'RIESTER', 'BETRIEBLICH']

FUND_BASE_NAV = [68.50, 42.10, 115.30, 52.80, 67.40, 89.20, 100.50, 35.60, 52.10, 1.00]
FUND_VOLATILITY = [0.012, 0.014, 0.011, 0.006, 0.009, 0.013, 0.003, 0.016, 0.004, 0.0005]

GERMAN_FIRST_NAMES = [
    'Hans', 'Klaus', 'Peter', 'Thomas', 'Michael', 'Andreas', 'Stefan', 'Markus',
    'Anna', 'Maria', 'Julia', 'Sandra', 'Christina', 'Sabine', 'Monika', 'Laura',
    'Felix', 'Leon', 'Lukas', 'Noah', 'Emma', 'Mia', 'Hannah', 'Lena'
]
GERMAN_LAST_NAMES = [
    'Mueller', 'Schmidt', 'Schneider', 'Fischer', 'Weber', 'Meyer', 'Wagner',
    'Becker', 'Schulz', 'Hoffmann', 'Koch', 'Bauer', 'Richter', 'Klein',
    'Wolf', 'Schroeder', 'Neumann', 'Schwarz', 'Zimmermann', 'Braun'
]


def generate_customers():
    print("Generating customers...")
    rows = []
    for i in range(1, NUM_CUSTOMERS + 1):
        dob = date(random.randint(1950, 1995), random.randint(1, 12), random.randint(1, 28))
        since = date(random.randint(2005, 2022), random.randint(1, 12), random.randint(1, 28))
        rows.append({
            'customer_code':  f'CUST-{i:05d}',
            'sparkasse_id':   random.randint(1, NUM_SPARKASSEN),
            'first_name':     random.choice(GERMAN_FIRST_NAMES),
            'last_name':      random.choice(GERMAN_LAST_NAMES),
            'date_of_birth':  dob.isoformat(),
            'customer_since': since.isoformat(),
            'risk_profile':   random.choices(
                RISK_PROFILES, weights=[30, 40, 20, 10]
            )[0],
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, 'customers.csv'), index=False)
    print(f"  -> {len(df)} customers written")
    return df


def generate_depots(customers_df):
    print("Generating depots...")
    rows = []
    depot_id = 1
    for _, cust in customers_df.iterrows():
        n_depots = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        for _ in range(n_depots):
            opened = date(random.randint(2010, 2023), random.randint(1, 12), random.randint(1, 28))
            rows.append({
                'depot_number':  f'DEP-{depot_id:06d}',
                'customer_id':   int(cust.name) + 1,
                'sparkasse_id':  int(cust['sparkasse_id']),
                'depot_type':    random.choices(DEPOT_TYPES, weights=[65, 15, 12, 8])[0],
                'opened_date':   opened.isoformat(),
            })
            depot_id += 1
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, 'depots.csv'), index=False)
    print(f"  -> {len(df)} depots written")
    return df


def generate_fund_nav():
    print("Generating fund NAV prices...")
    rows = []
    trading_days = pd.bdate_range(NAV_START, NAV_END)
    for fund_id in range(1, NUM_FUNDS + 1):
        price = FUND_BASE_NAV[fund_id - 1]
        vol   = FUND_VOLATILITY[fund_id - 1]
        for d in trading_days:
            price = max(price * (1 + np.random.normal(0.0002, vol)), 0.01)
            rows.append({
                'fund_id':   fund_id,
                'nav_date':  d.date().isoformat(),
                'nav_price': round(price, 4),
            })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, 'fund_nav.csv'), index=False)
    print(f"  -> {len(df)} NAV records written")
    return df


def generate_holdings(depots_df, nav_df):
    print("Generating holdings...")
    latest_nav = nav_df.groupby('fund_id')['nav_price'].last().to_dict()
    rows = []
    for depot_id in depots_df.index + 1:
        n_funds = random.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
        chosen_funds = random.sample(range(1, NUM_FUNDS + 1), n_funds)
        for fund_id in chosen_funds:
            units = round(random.uniform(10, 5000), 6)
            avg_price = round(latest_nav.get(fund_id, 100) * random.uniform(0.8, 1.2), 4)
            rows.append({
                'depot_id':           depot_id,
                'fund_id':            fund_id,
                'units':              units,
                'avg_purchase_price': avg_price,
            })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, 'holdings.csv'), index=False)
    print(f"  -> {len(df)} holdings written")
    return df


def generate_transactions(depots_df, nav_df):
    print("Generating transactions (with injected DQ errors)...")
    nav_lookup = nav_df.groupby(['fund_id', 'nav_date'])['nav_price'].first().to_dict()
    trading_days = sorted(nav_df['nav_date'].unique())
    rows = []

    for depot_id in depots_df.index + 1:
        n_txns = random.randint(5, 30)
        for _ in range(n_txns):
            fund_id = random.randint(1, NUM_FUNDS)
            txn_date = random.choice(trading_days[-500:])  # last ~2 years
            settlement_offset = random.choices([1, 2, 3], weights=[10, 80, 10])[0]
            settlement_date = (pd.Timestamp(txn_date) + pd.tseries.offsets.BusinessDay(settlement_offset)).date().isoformat()
            txn_type = random.choices(
                ['BUY', 'SELL', 'SWITCH_IN', 'SWITCH_OUT', 'DIVIDEND'],
                weights=[50, 25, 10, 10, 5]
            )[0]
            nav_price = nav_lookup.get((fund_id, txn_date))
            units = round(random.uniform(1, 500), 6)
            amount = round(units * (nav_price or 50), 2)
            fee = round(amount * random.uniform(0, 0.015), 2)
            rows.append({
                'depot_id':         depot_id,
                'fund_id':          fund_id,
                'transaction_date': txn_date,
                'settlement_date':  settlement_date,
                'transaction_type': txn_type,
                'units':            units,
                'nav_price':        nav_price,
                'amount_eur':       amount,
                'fee_eur':          fee,
                'status':           'SETTLED',
            })

    df = pd.DataFrame(rows)

    # ---- Inject intentional DQ errors (for Exercise 8) ----
    n = len(df)
    # a) ~1% negative amounts
    neg_idx = df.sample(frac=0.01, random_state=1).index
    df.loc[neg_idx, 'amount_eur'] = -df.loc[neg_idx, 'amount_eur']

    # b) ~0.5% settlement before trade date
    early_idx = df.sample(frac=0.005, random_state=2).index
    df.loc[early_idx, 'settlement_date'] = df.loc[early_idx, 'transaction_date']
    df.loc[early_idx, 'settlement_date'] = (
        pd.to_datetime(df.loc[early_idx, 'transaction_date']) - timedelta(days=1)
    ).dt.date.astype(str)

    # c) ~1% T+3 breaches
    late_idx = df.sample(frac=0.01, random_state=3).index
    df.loc[late_idx, 'settlement_date'] = (
        pd.to_datetime(df.loc[late_idx, 'transaction_date']) + timedelta(days=5)
    ).dt.date.astype(str)

    # d) ~1.5% NULL nav_price for settled records
    null_idx = df.sample(frac=0.015, random_state=4).index
    df.loc[null_idx, 'nav_price'] = None

    df.to_csv(os.path.join(OUTPUT_DIR, 'transactions.csv'), index=False)
    print(f"  -> {len(df)} transactions written (DQ errors injected)")
    return df


if __name__ == '__main__':
    print("=" * 50)
    print(" DekaBank Interview Prep - Data Generator")
    print("=" * 50)
    customers_df   = generate_customers()
    depots_df      = generate_depots(customers_df)
    nav_df         = generate_fund_nav()
    holdings_df    = generate_holdings(depots_df, nav_df)
    transactions_df = generate_transactions(depots_df, nav_df)
    print("=" * 50)
    print(f"Done! CSV files written to: {os.path.abspath(OUTPUT_DIR)}")
    print()
    print("Next steps:")
    print("  1. docker exec -i deka-db psql -U postgres < sql/01_schema.sql")
    print("  2. docker exec -i deka-db psql -U postgres < sql/02_seed_data.sql")
    print("  3. See README.md for \\copy commands to load CSVs")
