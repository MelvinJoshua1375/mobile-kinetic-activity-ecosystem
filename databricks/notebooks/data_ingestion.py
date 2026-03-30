# Databricks notebook source
# MAGIC %md
# MAGIC # Data Ingestion
# MAGIC
# MAGIC Reads `mobile_health.csv` into Delta Lake (DBFS), validates schema and row count,
# MAGIC and writes the raw table used by all downstream notebooks.
# MAGIC
# MAGIC **Columns:**  al_x, al_y, al_z, gl_x, gl_y, gl_z, ar_x, ar_y, ar_z, gr_x, gr_y, gr_z, Activity, subject

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CSV_PATH   = "dbfs:/FileStore/mobile_health/mobile_health.csv"
DELTA_PATH = "dbfs:/FileStore/mobile_health/delta/raw"

SENSOR_COLS = ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
               "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z"]
LABEL_COL   = "Activity"
SUBJECT_COL = "subject"
EXPECTED_COLS = SENSOR_COLS + [LABEL_COL, SUBJECT_COL]

# COMMAND ----------
# MAGIC %md ## 1. Read CSV

df_raw = (
    spark.read
    .option("header", "true")
    .option("inferSchema", "true")
    .csv(CSV_PATH)
)

# Show schema
df_raw.printSchema()

# COMMAND ----------
# MAGIC %md ## 2. Validate schema

actual_cols = set(df_raw.columns)
missing     = set(EXPECTED_COLS) - actual_cols
extra       = actual_cols - set(EXPECTED_COLS)

assert not missing, f"Missing columns: {missing}"
print(f"Extra columns (will keep): {extra}")
print("Schema validation PASSED ✓")

# COMMAND ----------
# MAGIC %md ## 3. Cast & clean types

df_typed = df_raw
for col in SENSOR_COLS:
    df_typed = df_typed.withColumn(col, F.col(col).cast(DoubleType()))

df_typed = df_typed.withColumn(LABEL_COL, F.col(LABEL_COL).cast(IntegerType()))

# COMMAND ----------
# MAGIC %md ## 4. Null check

null_counts = {c: df_typed.filter(F.col(c).isNull()).count() for c in EXPECTED_COLS}
for col, n in null_counts.items():
    if n > 0:
        print(f"WARNING: {col} has {n} nulls — dropping rows")

df_clean = df_typed.dropna(subset=EXPECTED_COLS)

row_count = df_clean.count()
print(f"Rows after null removal: {row_count:,}")
assert row_count > 1_000_000, f"Expected ~1.2M rows, got {row_count:,}"

# COMMAND ----------
# MAGIC %md ## 5. Activity distribution

display(
    df_clean
    .groupBy(LABEL_COL)
    .agg(F.count("*").alias("count"))
    .withColumn("pct", F.round(F.col("count") / row_count * 100, 2))
    .orderBy(LABEL_COL)
)

# COMMAND ----------
# MAGIC %md ## 6. Write Delta table

(
    df_clean
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .save(DELTA_PATH)
)

print(f"Written to {DELTA_PATH}")
print("01_data_ingestion COMPLETE ✓")
