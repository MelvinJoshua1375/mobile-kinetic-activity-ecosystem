# Databricks notebook source
# MAGIC %md
# MAGIC # 02 — Exploratory Data Analysis
# MAGIC
# MAGIC Reads the raw Delta table and produces:
# MAGIC - Per-sensor descriptive statistics
# MAGIC - Correlation heatmap data
# MAGIC - Activity × subject cross-tabulation
# MAGIC - IQR-based outlier counts (pre-treatment summary)

# COMMAND ----------

from pyspark.sql import functions as F
import json

DELTA_PATH = "dbfs:/FileStore/mobile_health/delta/raw"

SENSOR_COLS = ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
               "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z"]
LABEL_COL   = "Activity"
SUBJECT_COL = "subject"

# COMMAND ----------
# MAGIC %md ## 1. Load raw data

df = spark.read.format("delta").load(DELTA_PATH).cache()
print(f"Total rows: {df.count():,}")

# COMMAND ----------
# MAGIC %md ## 2. Descriptive statistics

display(df.select(SENSOR_COLS).describe())

# COMMAND ----------
# MAGIC %md ## 3. Activity distribution

display(
    df.groupBy(LABEL_COL)
      .count()
      .withColumn("pct", F.round(F.col("count") / df.count() * 100, 2))
      .orderBy(LABEL_COL)
)

# COMMAND ----------
# MAGIC %md ## 4. Subject distribution

display(
    df.groupBy(SUBJECT_COL)
      .count()
      .orderBy(SUBJECT_COL)
)

# COMMAND ----------
# MAGIC %md ## 5. IQR outlier summary (per column)

def iqr_outlier_count(df, col):
    q1, q3 = df.approxQuantile(col, [0.25, 0.75], 0.01)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return df.filter((F.col(col) < lo) | (F.col(col) > hi)).count()

print("\nOutlier counts per sensor (IQR method):")
for col in SENSOR_COLS:
    n = iqr_outlier_count(df, col)
    pct = n / df.count() * 100
    print(f"  {col:8s}: {n:>7,}  ({pct:.2f}%)")

# COMMAND ----------
# MAGIC %md ## 6. Pearson correlation matrix

from pyspark.ml.stat import Correlation
from pyspark.ml.feature import VectorAssembler

assembler = VectorAssembler(inputCols=SENSOR_COLS, outputCol="features")
df_vec    = assembler.transform(df)

corr_matrix = Correlation.corr(df_vec, "features").collect()[0][0]
corr_list   = corr_matrix.toArray().tolist()

print("Correlation matrix (rows/cols = SENSOR_COLS):")
for row in corr_list:
    print([round(v, 3) for v in row])

# COMMAND ----------
# MAGIC %md ## 7. Activity × Subject cross-tab

display(df.crosstab(LABEL_COL, SUBJECT_COL))

# COMMAND ----------

df.unpersist()
print("eda COMPLETE ✓")
