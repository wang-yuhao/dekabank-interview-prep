"""
PySpark Use Case 2 — Delta Lake SCD Type 2 (Slowly Changing Dimensions)
=========================================================================
Simulates the client risk-category dimension table changing over time.
Uses the client_segments.csv dataset in data/ (run generate_pyspark_data.py first).

Why SCD Type 2 matters at DekaBank:
  A client upgrades from CONSERVATIVE → GROWTH profile.
  Regulators require we keep the full history of which product was sold
  to which client under which risk classification.

Run locally:
    pip install pyspark delta-spark pandas
    python pyspark/generate_pyspark_data.py   # create client_segments.csv
    python pyspark/02_delta_scd2.py

What you will see:
    Step 1  Load initial snapshot → write as Delta table
    Step 2  Apply updates (simulate new data arriving)
    Step 3  MERGE: expire old records, insert new versions
    Step 4  Query: current view (is_current=true)
    Step 5  Time-travel: rewind to before the changes
"""

import os, shutil
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from delta import configure_spark_with_delta_pip

# ── Bootstrap ────────────────────────────────────────────────────────
builder = (SparkSession.builder
    .appName("DekaBank-SCD2")
    .master("local[*]")
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
    .config("spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog")
    .config("spark.sql.shuffle.partitions", "4"))

spark = configure_spark_with_delta_pip(builder).getOrCreate()
spark.sparkContext.setLogLevel("WARN")

DATA_DIR   = os.path.join(os.path.dirname(__file__), "..", "data")
DELTA_PATH = os.path.join(DATA_DIR, "delta_dim_client")
SEG_PATH   = os.path.join(DATA_DIR, "client_segments.csv")

# ── Clean previous run ───────────────────────────────────────────────
if os.path.exists(DELTA_PATH):
    shutil.rmtree(DELTA_PATH)

# ── Step 1: Load initial snapshot ───────────────────────────────────
print("=" * 60)
print("STEP 1  Load initial snapshot")
print("=" * 60)

df_raw = (spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(SEG_PATH))

# Keep only the earliest record per customer as our "initial load"
w_init = Window.partitionBy("customer_id").orderBy("effective_from")
df_initial = (df_raw
    .withColumn("rn", F.row_number().over(w_init))
    .filter(F.col("rn") == 1)
    .drop("rn"))

# Add SCD2 bookkeeping columns
df_dim = (df_initial
    .withColumn("start_date",  F.col("effective_from").cast("date"))
    .withColumn("end_date",    F.lit("9999-12-31").cast("date"))
    .withColumn("is_current",  F.lit(True))
    .withColumn("record_hash", F.md5(F.concat_ws("|", "risk_category", "credit_tier")))
    .drop("effective_from"))

# Write as Delta table
df_dim.write.format("delta").mode("overwrite").save(DELTA_PATH)
print(f"Initial snapshot: {df_dim.count()} records written to Delta table")
df_dim.show(5)


# ── Step 2: Prepare incoming updates ───────────────────────────────
print("=" * 60)
print("STEP 2  Incoming updates (customers who changed risk category)")
print("=" * 60)

# These are the 'new' records that arrived — the 2024-03-15 changes
w_latest = Window.partitionBy("customer_id").orderBy(F.col("effective_from").desc())
df_updates_raw = (df_raw
    .withColumn("rn", F.row_number().over(w_latest))
    .filter(F.col("rn") == 1)   # latest record per customer
    .drop("rn"))

df_updates = (df_updates_raw
    .withColumn("start_date",  F.col("effective_from").cast("date"))
    .withColumn("end_date",    F.lit("9999-12-31").cast("date"))
    .withColumn("is_current",  F.lit(True))
    .withColumn("record_hash", F.md5(F.concat_ws("|", "risk_category", "credit_tier")))
    .drop("effective_from"))

print(f"Updates to apply: {df_updates.count()} records")
df_updates.show(5)


# ── Step 3: MERGE  (SCD Type 2 pattern) ────────────────────────────
print("=" * 60)
print("STEP 3  MERGE — expire old records, insert new versions")
print("=" * 60)

from delta.tables import DeltaTable

target = DeltaTable.forPath(spark, DELTA_PATH)

(target.alias("target")
 .merge(
    df_updates.alias("source"),
    # Only match active (is_current=true) records where data changed
    """
    target.customer_id = source.customer_id
    AND target.is_current = true
    AND target.record_hash <> source.record_hash
    """
 )
 # Expire the old row: set end_date and flip is_current flag
 .whenMatchedUpdate(set={
    "end_date":   "current_date()",
    "is_current": "false"
 })
 # Insert the new version as a brand-new active row
 .whenNotMatchedInsert(values={
    "customer_id":   "source.customer_id",
    "risk_category": "source.risk_category",
    "credit_tier":   "source.credit_tier",
    "start_date":    "source.start_date",
    "end_date":      "source.end_date",
    "is_current":    "source.is_current",
    "record_hash":   "source.record_hash",
 })
 .execute()
)
print("MERGE complete!")


# ── Step 4: Current view ─────────────────────────────────────────────
print("=" * 60)
print("STEP 4  Current view (is_current = true)")
print("=" * 60)

df_current = spark.read.format("delta").load(DELTA_PATH).filter(F.col("is_current"))
print(f"Current records: {df_current.count()}")
df_current.orderBy("customer_id").show(10)

print("Full history (all versions):")
spark.read.format("delta").load(DELTA_PATH).orderBy("customer_id", "start_date").show(20)


# ── Step 5: Time-travel  ─────────────────────────────────────────────
print("=" * 60)
print("STEP 5  Time-travel — see table before the MERGE (version 0)")
print("=" * 60)

df_v0 = spark.read.format("delta").option("versionAsOf", 0).load(DELTA_PATH)
print(f"Version 0 (initial snapshot): {df_v0.count()} records")
df_v0.show(5)

# Show the table history
target.history().select("version", "timestamp", "operation").show()
# Interview talking point:
# "Delta Lake auto-tracks every write. For MiFID II or BaFin audits,
#  we can replay any historical state with .option(versionAsOf, N).
#  No manual backup needed — it's built into the format."

spark.stop()
print("\nSCD Type 2 use case complete.")
