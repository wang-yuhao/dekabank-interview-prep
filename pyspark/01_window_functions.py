"""
PySpark Use Case 1 — Window Functions on Fund NAV Data
=======================================================
Demonstrates ROW_NUMBER, LAG, and rolling AVG window functions
using the existing fund_nav.csv dataset from this repo.

Run locally (no real Spark cluster needed):
    pip install pyspark findspark pandas
    python pyspark/01_window_functions.py

What you will see:
    UC-1  Latest NAV per fund (row_number trick)
    UC-2  Daily price-change % per fund (lag)
    UC-3  30-day rolling average NAV per fund
    UC-4  Anomaly detection: flag price moves > 5%
"""

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
import os

# ── Bootstrap ────────────────────────────────────────────────────────
spark = (SparkSession.builder
         .appName("DekaBank-WindowFunctions")
         .master("local[*]")
         .config("spark.sql.shuffle.partitions", "4")   # small dataset → keep it fast
         .getOrCreate())
spark.sparkContext.setLogLevel("WARN")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
NAV_PATH  = os.path.join(DATA_DIR, "fund_nav.csv")

# ── Load data ────────────────────────────────────────────────────────
df = (spark.read
      .option("header", "true")
      .option("inferSchema", "true")
      .csv(NAV_PATH)
      .withColumn("nav_date", F.to_date("nav_date")))

print(f"Loaded {df.count():,} NAV rows for {df.select('fund_id').distinct().count()} funds\n")
df.printSchema()


# ═══════════════════════════════════════════════════════════════════════
# UC-1  Latest NAV per fund
# ─────────────────────────────────────────────────────────────────────
# PARTITION BY fund_id → treat each fund independently
# ORDER BY nav_date DESC → most recent date gets rank 1
# Filter rn == 1 → keep only latest row per fund
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("UC-1  Latest NAV per fund (ROW_NUMBER)")
print("=" * 60)

w_latest = Window.partitionBy("fund_id").orderBy(F.col("nav_date").desc())

df_latest = (df
    .withColumn("rn", F.row_number().over(w_latest))
    .filter(F.col("rn") == 1)
    .drop("rn")
    .orderBy("fund_id"))

df_latest.show(10)
# Interview talking point:
# "ROW_NUMBER assigns 1 to the most recent row per fund.
#  We keep only rn==1 — effectively a distributed 'latest record' lookup
#  that runs on all 10 funds in parallel across the cluster."


# ═══════════════════════════════════════════════════════════════════════
# UC-2  Daily price-change % per fund  (LAG)
# ─────────────────────────────────────────────────────────────────────
# LAG(nav_price, 1) looks back 1 row within the same fund partition,
# ordered by date ascending → gives yesterday's price
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("UC-2  Daily % change per fund (LAG)")
print("=" * 60)

w_ordered = Window.partitionBy("fund_id").orderBy("nav_date")

df_changes = (df
    .withColumn("prev_nav",    F.lag("nav_price", 1).over(w_ordered))
    .withColumn("pct_change",  F.round(
        (F.col("nav_price") - F.col("prev_nav")) / F.col("prev_nav") * 100, 4))
    .filter(F.col("prev_nav").isNotNull()))   # drop first row per fund (no prev day)

df_changes.filter(F.col("fund_id") == 1).orderBy("nav_date").show(10)
# Interview talking point:
# "LAG is essential for any time-series comparison in finance.
#  The PARTITION BY ensures we never accidentally compare fund 2's
#  last price to fund 1's first price."


# ═══════════════════════════════════════════════════════════════════════
# UC-3  30-day rolling average NAV per fund
# ─────────────────────────────────────────────────────────────────────
# rowsBetween(-29, 0) = current row + 29 preceding rows = 30 rows max
# When fewer than 30 rows exist (beginning of history), Spark
# automatically uses however many rows are available.
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("UC-3  30-day rolling average NAV (rowsBetween)")
print("=" * 60)

w_rolling = (Window.partitionBy("fund_id")
             .orderBy("nav_date")
             .rowsBetween(-29, 0))

df_rolling = (df_changes   # reuse df with prev_nav already computed
    .withColumn("rolling_30d_avg",
                F.round(F.avg("nav_price").over(w_rolling), 4)))

df_rolling.filter(F.col("fund_id") == 1).orderBy("nav_date").show(10)
# Interview talking point:
# "rowsBetween is physical row-based. rangeBetween would be value-based
#  (e.g., +/-30 in the actual numeric date value). For evenly-spaced
#  trading-day data rowsBetween is cleaner and more predictable."


# ═══════════════════════════════════════════════════════════════════════
# UC-4  Anomaly detection — flag price moves > 5%
# ─────────────────────────────────────────────────────────────────────
# Combines UC-2 and UC-3:
#   abs(pct_change) > 5  → sudden spike/crash
# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("UC-4  Anomaly flags (|pct_change| > 5%)")
print("=" * 60)

df_anomalies = (df_rolling
    .withColumn("is_anomaly", F.abs(F.col("pct_change")) > 5)
    .filter(F.col("is_anomaly")))

df_anomalies.select("fund_id", "nav_date", "nav_price", "prev_nav", "pct_change") \
            .orderBy(F.abs(F.col("pct_change")).desc()) \
            .show(20)

print("Anomaly count per fund:")
df_anomalies.groupBy("fund_id").count().orderBy("fund_id").show()
# Interview talking point:
# "In a real pipeline, anomalies would be written to a quarantine
#  Delta table with the full row + a reason code. The Gold layer
#  would NEVER contain unreviewed anomalies."

spark.stop()
print("\nAll window-function use cases complete.")
