# Databricks notebook source
# MAGIC %md
# MAGIC # 05 — Anomaly Detection
# MAGIC
# MAGIC Uses a 10% stratified sample to fit:
# MAGIC - Isolation Forest (sklearn) — primary detector
# MAGIC - Local Outlier Factor (sklearn) — secondary detector
# MAGIC
# MAGIC Scores anomalies on the full clustered dataset and writes:
# MAGIC - `anomalies.json` — top anomaly records for UI display
# MAGIC - `anomaly_thresholds.json` — decision thresholds for inference

# COMMAND ----------

import json
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor

CLUSTERED_PATH    = "dbfs:/FileStore/mobile_health/delta/clustered"
ANOMALY_JSON      = "/dbfs/FileStore/mobile_health/anomalies.json"
THRESHOLD_JSON    = "/dbfs/FileStore/mobile_health/anomaly_thresholds.json"
CENTROIDS_JSON    = "/dbfs/FileStore/mobile_health/centroids.json"

FEATURE_COLS = ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
                "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z",
                "al_mag","gl_mag","ar_mag","gr_mag"]
LABEL_COL    = "Activity"
SUBJECT_COL  = "subject"
SAMPLE_FRAC  = 0.10
SEED         = 42

# COMMAND ----------
# MAGIC %md ## 1. Load clustered data

df = spark.read.format("delta").load(CLUSTERED_PATH).cache()
n_total = df.count()
print(f"Total rows: {n_total:,}")

# COMMAND ----------
# MAGIC %md ## 2. Stratified sample for model fitting

# 10% stratified by Activity label
fractions = {
    row[LABEL_COL]: SAMPLE_FRAC
    for row in df.select(LABEL_COL).distinct().collect()
}
df_sample = df.sampleBy(LABEL_COL, fractions=fractions, seed=SEED).cache()
n_sample  = df_sample.count()
print(f"Sample size: {n_sample:,}  ({n_sample/n_total*100:.1f}%)")

X_sample = np.array(
    df_sample.select(FEATURE_COLS).collect()
)

# COMMAND ----------
# MAGIC %md ## 3. Fit Isolation Forest

iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=SEED, n_jobs=-1)
iso.fit(X_sample)
print("Isolation Forest fitted ✓")

# COMMAND ----------
# MAGIC %md ## 4. Fit LOF (novelty=True so we can score new data)

lof = LocalOutlierFactor(n_neighbors=20, contamination=0.05, novelty=True, n_jobs=-1)
lof.fit(X_sample)
print("LOF fitted ✓")

# COMMAND ----------
# MAGIC %md ## 5. Score full dataset (in batches to avoid OOM)

BATCH = 50_000

df_pd    = df.select(FEATURE_COLS + [LABEL_COL, SUBJECT_COL, "prediction"]).toPandas()
X_full   = df_pd[FEATURE_COLS].values

iso_scores = iso.score_samples(X_full)   # more negative = more anomalous
lof_scores = lof.score_samples(X_full)   # more negative = more anomalous

# Combine into a single anomaly score (average of normalised scores)
def minmax(arr):
    lo, hi = arr.min(), arr.max()
    return (arr - lo) / (hi - lo + 1e-9)

combined = (minmax(iso_scores) + minmax(lof_scores)) / 2  # 0=normal, 1=anomaly (inverted below)
anomaly_score = 1 - combined  # now 1 = most anomalous

df_pd["iso_score"]     = iso_scores
df_pd["lof_score"]     = lof_scores
df_pd["anomaly_score"] = anomaly_score
df_pd["is_anomaly"]    = (anomaly_score > np.percentile(anomaly_score, 95)).astype(int)

n_anomalies = df_pd["is_anomaly"].sum()
print(f"Flagged anomalies: {n_anomalies:,}  ({n_anomalies/len(df_pd)*100:.2f}%)")

# COMMAND ----------
# MAGIC %md ## 6. Save top anomalies to JSON

top_anomalies = (
    df_pd[df_pd["is_anomaly"] == 1]
    .sort_values("anomaly_score", ascending=False)
    .head(500)
)

anomaly_records = top_anomalies[
    FEATURE_COLS + [LABEL_COL, SUBJECT_COL, "prediction", "anomaly_score", "iso_score", "lof_score"]
].rename(columns={LABEL_COL: "activity", SUBJECT_COL: "subject", "prediction": "cluster"}).to_dict(orient="records")

# Round floats for smaller JSON
for rec in anomaly_records:
    for k, v in rec.items():
        if isinstance(v, float):
            rec[k] = round(v, 6)

with open(ANOMALY_JSON, "w") as f:
    json.dump({"total_anomalies": int(n_anomalies), "records": anomaly_records}, f, indent=2)
print(f"anomalies.json written ({len(anomaly_records)} records) ✓")

# COMMAND ----------
# MAGIC %md ## 7. Save thresholds

thresholds = {
    "iso_threshold":     float(np.percentile(iso_scores, 5)),   # below = anomaly
    "lof_threshold":     float(np.percentile(lof_scores, 5)),
    "combined_threshold": float(np.percentile(anomaly_score, 95)),
}

with open(THRESHOLD_JSON, "w") as f:
    json.dump(thresholds, f, indent=2)
print(f"anomaly_thresholds.json written ✓")

# COMMAND ----------
# MAGIC %md ## 8. Save centroids for inference endpoint

kmeans_stats_path = "/dbfs/FileStore/mobile_health/cluster_stats.json"
with open(kmeans_stats_path) as f:
    cluster_stats = json.load(f)

centroids = {
    cid: stats["feature_means"]
    for cid, stats in cluster_stats.items()
}

with open(CENTROIDS_JSON, "w") as f:
    json.dump(centroids, f, indent=2)
print(f"centroids.json written ✓")

# COMMAND ----------

df.unpersist()
df_sample.unpersist()
print("anomaly_detection COMPLETE ✓")
