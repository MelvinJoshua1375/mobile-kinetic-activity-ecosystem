# Databricks notebook source
# MAGIC %md
# MAGIC # 03 — Feature Engineering
# MAGIC
# MAGIC Fixes the original notebook's critical bugs:
# MAGIC - Bug 1: Outlier-cleaned data was never used in modelling (cleaned df dropped)
# MAGIC - Bug 2: Only 6/12 sensor columns were cleaned
# MAGIC - Bug 3: Preprocessing pipeline (VectorAssembler + MinMaxScaler) was never saved
# MAGIC
# MAGIC Pipeline:
# MAGIC 1. IQR winsorization (clip, not drop) on ALL 12 sensor columns
# MAGIC 2. Add 4 magnitude features: al_mag, gl_mag, ar_mag, gr_mag
# MAGIC 3. Fit VectorAssembler + MinMaxScaler pipeline
# MAGIC 4. Save the fitted pipeline to DBFS so the backend can reload it
# MAGIC 5. Write feature-engineered Delta table

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import VectorAssembler, MinMaxScaler
import json

RAW_DELTA_PATH      = "dbfs:/FileStore/mobile_health/delta/raw"
FEATURE_DELTA_PATH  = "dbfs:/FileStore/mobile_health/delta/features"
PIPELINE_SAVE_PATH  = "dbfs:/FileStore/mobile_health/pipeline"

SENSOR_COLS = ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
               "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z"]
MAG_COLS    = ["al_mag","gl_mag","ar_mag","gr_mag"]
FEATURE_COLS = SENSOR_COLS + MAG_COLS
LABEL_COL   = "Activity"
SUBJECT_COL = "subject"

# COMMAND ----------
# MAGIC %md ## 1. Load raw data

df = spark.read.format("delta").load(RAW_DELTA_PATH).cache()
print(f"Loaded {df.count():,} rows")

# COMMAND ----------
# MAGIC %md ## 2. IQR winsorization — ALL 12 sensor columns (Bug fix: was 6)

def winsorize(df, cols, quantile_error=0.01):
    """Clip values to [Q1-1.5*IQR, Q3+1.5*IQR] for each column."""
    bounds = {}
    for col in cols:
        q1, q3 = df.approxQuantile(col, [0.25, 0.75], quantile_error)
        iqr = q3 - q1
        lo  = q1 - 1.5 * iqr
        hi  = q3 + 1.5 * iqr
        bounds[col] = (lo, hi)
        df = df.withColumn(col, F.least(F.greatest(F.col(col), F.lit(lo)), F.lit(hi)))
    return df, bounds

df_clean, iqr_bounds = winsorize(df, SENSOR_COLS)

# Persist IQR bounds for backend inference (anomaly scoring)
iqr_bounds_serializable = {k: list(v) for k, v in iqr_bounds.items()}
bounds_json_path = "/dbfs/FileStore/mobile_health/iqr_bounds.json"
with open(bounds_json_path, "w") as f:
    json.dump(iqr_bounds_serializable, f)
print(f"IQR bounds saved to {bounds_json_path}")

# Sanity check: no more extreme outliers
print("\nPost-winsorization range check:")
for col in SENSOR_COLS:
    lo, hi = iqr_bounds[col]
    remaining = df_clean.filter((F.col(col) < lo) | (F.col(col) > hi)).count()
    assert remaining == 0, f"{col} still has outliers after winsorization"
print("All sensors winsorized ✓")

# COMMAND ----------
# MAGIC %md ## 3. Magnitude features

df_feat = (
    df_clean
    .withColumn("al_mag", F.sqrt(F.col("al_x")**2 + F.col("al_y")**2 + F.col("al_z")**2))
    .withColumn("gl_mag", F.sqrt(F.col("gl_x")**2 + F.col("gl_y")**2 + F.col("gl_z")**2))
    .withColumn("ar_mag", F.sqrt(F.col("ar_x")**2 + F.col("ar_y")**2 + F.col("ar_z")**2))
    .withColumn("gr_mag", F.sqrt(F.col("gr_x")**2 + F.col("gr_y")**2 + F.col("gr_z")**2))
)

print(f"Features: {FEATURE_COLS}")

# COMMAND ----------
# MAGIC %md ## 4. Fit preprocessing pipeline (Bug fix: save it!)

assembler = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_features")
scaler    = MinMaxScaler(inputCol="raw_features", outputCol="features")

pipeline  = Pipeline(stages=[assembler, scaler])
pipeline_model = pipeline.fit(df_feat)

# Save to DBFS — backend uses this for inference
pipeline_model.write().overwrite().save(PIPELINE_SAVE_PATH)
print(f"Pipeline saved to {PIPELINE_SAVE_PATH} ✓")

# COMMAND ----------
# MAGIC %md ## 5. Transform & write features Delta table

df_transformed = pipeline_model.transform(df_feat)

# Keep only what downstream needs
df_out = df_transformed.select(
    FEATURE_COLS + [LABEL_COL, SUBJECT_COL, "features"]
)

(
    df_out
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .save(FEATURE_DELTA_PATH)
)

count = df_out.count()
print(f"Written {count:,} rows to {FEATURE_DELTA_PATH} ✓")

# COMMAND ----------

df.unpersist()
print("feature_engineering COMPLETE ✓")
