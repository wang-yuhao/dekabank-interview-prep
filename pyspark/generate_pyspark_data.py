"""
Extra data generator for PySpark use cases.
Run this AFTER python/generate_data.py

Outputs:
    data/client_segments.csv  — used by 02_delta_scd2.py (SCD Type 2)
"""

import os
import numpy as np
import pandas as pd

np.random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

RISK_PROFILES = ['CONSERVATIVE', 'BALANCED', 'GROWTH', 'AGGRESSIVE']
customer_ids  = [f'CUST-{i:05d}' for i in range(1, 51)]

rows = []
for cid in customer_ids:
    profile = np.random.choice(RISK_PROFILES, p=[0.3, 0.4, 0.2, 0.1])
    rows.append({
        'customer_id':   cid,
        'risk_category': profile,
        'credit_tier':   np.random.choice(['A', 'B', 'C'], p=[0.5, 0.35, 0.15]),
        'effective_from': '2022-01-01',
    })
    if np.random.random() < 0.4:
        new_profile = np.random.choice([p for p in RISK_PROFILES if p != profile])
        rows.append({
            'customer_id':   cid,
            'risk_category': new_profile,
            'credit_tier':   np.random.choice(['A', 'B', 'C'], p=[0.5, 0.35, 0.15]),
            'effective_from': '2024-03-15',
        })

df = pd.DataFrame(rows)
path = os.path.join(OUTPUT_DIR, 'client_segments.csv')
df.to_csv(path, index=False)
print(f"Generated {len(df)} rows -> {path}")
print(df.head(10).to_string())
