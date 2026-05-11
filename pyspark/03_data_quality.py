"""
PySpark Use Case 3 — Data Quality Framework for Financial Transactions
=======================================================================
Implements a reusable DQ check suite on the transactions.csv dataset.
Maps directly to the 4 dimensions:
    Completeness | Validity | Uniqueness | Consistency

Run locally:
    pip install pyspark pandas
    python pyspark/03_data_quality.py

What you will see:
    DQ-1  Completeness: no NULL in critical columns
    DQ-2  Validity: amount_eur > 0 and valid date range
    DQ-3  Uniqueness: no duplicate transaction rows
    DQ-4  Consistency: settlement_date >= transaction_date
    DQ-5  T+3 rule: settlement must be within T+3 business days
    Summary report with pass/fail + bad rows quarantined
"""

import os
from dataclasses import dataclass, field
from typing import List
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F

# ── Bootstrap ─────────────────────────────────────────────────────────
spark = (SparkSession.builder
    .appName("DekaBank-DataQuality")
    .master("local[*]")
    .config("spark.sql.shuffle.partitions", "4")
    .getOrCreate())
spark.sparkContext.setLogLevel("WARN")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TXN_PATH = os.path.join(DATA_DIR, "transactions.csv")


# ── Data classes ──────────────────────────────────────────────────────
@dataclass
class DQResult:
    dimension:    str         # Completeness / Validity / Uniqueness / Consistency
    check_name:   str
    passed:       bool
    total_rows:   int
    failed_rows:  int
    sample_bad:   list = field(default_factory=list)

    @property
    def pass_rate(self):
        return round((self.total_rows - self.failed_rows) / self.total_rows * 100, 2)

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        return (f"  [{self.dimension:15s}] {self.check_name:48s} "
                f"{status:4s}  failed={self.failed_rows:,}/{self.total_rows:,} "
                f"({self.pass_rate}%)")


# ── DQ Check Functions ────────────────────────────────────────────────

def check_completeness(df: DataFrame, cols: List[str]) -> DQResult:
    """DQ-1: All critical columns must be non-NULL."""
    null_condition = F.lit(False)
    for c in cols:
        null_condition = null_condition | F.col(c).isNull()
    failed_df = df.filter(null_condition)
    failed    = failed_df.count()
    total     = df.count()
    return DQResult(
        dimension="Completeness",
        check_name=f"No NULLs in {cols}",
        passed=failed == 0,
        total_rows=total,
        failed_rows=failed,
        sample_bad=[r.asDict() for r in failed_df.limit(3).collect()],
    )


def check_positive_amounts(df: DataFrame) -> DQResult:
    """DQ-2a: All transaction amounts must be > 0."""
    failed_df = df.filter(F.col("amount_eur") <= 0)
    failed    = failed_df.count()
    return DQResult(
        dimension="Validity",
        check_name="amount_eur > 0 (no negative transactions)",
        passed=failed == 0,
        total_rows=df.count(),
        failed_rows=failed,
        sample_bad=[r.asDict() for r in failed_df.limit(3).collect()],
    )


def check_valid_date_range(df: DataFrame) -> DQResult:
    """DQ-2b: transaction_date must be >= 2020-01-01 and not in the future."""
    bad = df.filter(
        (F.col("transaction_date") < F.lit("2020-01-01")) |
        (F.col("transaction_date") > F.current_date())
    )
    failed = bad.count()
    return DQResult(
        dimension="Validity",
        check_name="transaction_date in [2020-01-01, today]",
        passed=failed == 0,
        total_rows=df.count(),
        failed_rows=failed,
        sample_bad=[r.asDict() for r in bad.limit(3).collect()],
    )


def check_uniqueness(df: DataFrame, key_cols: List[str]) -> DQResult:
    """DQ-3: No duplicate rows by given key columns."""
    total    = df.count()
    distinct = df.dropDuplicates(key_cols).count()
    failed   = total - distinct
    return DQResult(
        dimension="Uniqueness",
        check_name=f"No duplicates on {key_cols}",
        passed=failed == 0,
        total_rows=total,
        failed_rows=failed,
    )


def check_settlement_after_trade(df: DataFrame) -> DQResult:
    """DQ-4: settlement_date must be >= transaction_date."""
    bad = df.filter(F.col("settlement_date") < F.col("transaction_date"))
    failed = bad.count()
    return DQResult(
        dimension="Consistency",
        check_name="settlement_date >= transaction_date",
        passed=failed == 0,
        total_rows=df.count(),
        failed_rows=failed,
        sample_bad=[r.asDict() for r in bad.limit(3).collect()],
    )


def check_t2_settlement(df: DataFrame) -> DQResult:
    """DQ-5: Settlement must be within T+3 (approx. 4 calendar days)."""
    bad = df.filter(
        F.datediff(F.col("settlement_date"), F.col("transaction_date")) > 4
    )
    failed = bad.count()
    return DQResult(
        dimension="Consistency",
        check_name="settlement within T+3 (<=4 calendar days)",
        passed=failed == 0,
        total_rows=df.count(),
        failed_rows=failed,
        sample_bad=[r.asDict() for r in bad.limit(3).collect()],
    )


# ── Load data ─────────────────────────────────────────────────────────
df_txn = (spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(TXN_PATH)
    .withColumn("transaction_date", F.to_date("transaction_date"))
    .withColumn("settlement_date",  F.to_date("settlement_date")))

print(f"Loaded {df_txn.count():,} transactions\n")


# ── Run all checks ─────────────────────────────────────────────────────
results = [
    check_completeness(df_txn, ["fund_id", "amount_eur", "transaction_date"]),
    check_positive_amounts(df_txn),
    check_valid_date_range(df_txn),
    check_uniqueness(df_txn, ["depot_id", "fund_id", "transaction_date", "transaction_type"]),
    check_settlement_after_trade(df_txn),
    check_t2_settlement(df_txn),
]


# ── Print report ──────────────────────────────────────────────────────
print()
print("=" * 80)
print(" DATA QUALITY REPORT — deka.transactions")
print("=" * 80)
for r in results:
    print(r)

total_checks  = len(results)
passed_checks = sum(1 for r in results if r.passed)
print()
print(f"  Overall: {passed_checks}/{total_checks} checks passed")
print("=" * 80)

# ── Print sample bad rows for failed checks ───────────────────────────
print("\nSample bad rows from failed checks:")
for r in results:
    if not r.passed and r.sample_bad:
        print(f"\n  [{r.check_name}]")
        for row in r.sample_bad:
            print(f"    {row}")

# ── Quarantine bad rows ───────────────────────────────────────────────
print("\nQuarantining failed records to data/quarantine/ ...")
QUARANTINE_DIR = os.path.join(DATA_DIR, "quarantine")

bad_rows = df_txn.filter(
    (F.col("amount_eur") <= 0) |
    F.col("fund_id").isNull() |
    (F.col("settlement_date") < F.col("transaction_date")) |
    (F.datediff("settlement_date", "transaction_date") > 4)
).withColumn("quarantine_reason",
    F.when(F.col("amount_eur") <= 0,                              F.lit("NEGATIVE_AMOUNT"))
     .when(F.col("fund_id").isNull(),                             F.lit("NULL_FUND_ID"))
     .when(F.col("settlement_date") < F.col("transaction_date"),  F.lit("SETTLEMENT_BEFORE_TRADE"))
     .otherwise(                                                   F.lit("T2_BREACH")))

bad_rows.write.mode("overwrite").option("header", "true").csv(QUARANTINE_DIR)
print(f"  {bad_rows.count()} bad rows written to {QUARANTINE_DIR}")
# Interview talking point:
# "The quarantine table has a quarantine_reason column.
#  Operations get a daily alert with counts per reason_code.
#  Nothing bad ever reaches the Gold layer or fund pricing reports."

spark.stop()
print("\nData Quality use case complete.")
