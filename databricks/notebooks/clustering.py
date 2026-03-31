# Databricks notebook source
# MAGIC %md
# MAGIC # 04 — Clustering
# MAGIC
# MAGIC Fixes:
# MAGIC - Bug: Original used only KMeans with k=2–9; we compare KMeans, BisectingKMeans,
# MAGIC   and GaussianMixture with k=2–15, tracking all runs in MLflow
# MAGIC - Bug: CSV re-read 16× in the elbow loop; now reads cached Delta once
# MAGIC - Bug: Optimal model was not saved; now saved + centroid JSON exported
# MAGIC
# MAGIC Outputs:
# MAGIC - Best KMeans model to DBFS
# MAGIC - `cluster_stats.json` with per-cluster raw-unit statistics
# MAGIC - `experiment_results.json` for the ExperimentTracker UI panel

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.ml.clustering import KMeans, BisectingKMeans, GaussianMixture
from pyspark.ml.evaluation import ClusteringEvaluator
import mlflow
import mlflow.spark
import json, math

FEATURE_DELTA_PATH = "dbfs:/FileStore/mobile_health/delta/features"
CLUSTERED_PATH     = "dbfs:/FileStore/mobile_health/delta/clustered"
MODEL_SAVE_PATH    = "dbfs:/FileStore/mobile_health/kmeans_model"
STATS_JSON_PATH    = "/dbfs/FileStore/mobile_health/cluster_stats.json"
EXPERIMENT_JSON    = "/dbfs/FileStore/mobile_health/experiment_results.json"

FEATURE_COLS = ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
                "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z",
                "al_mag","gl_mag","ar_mag","gr_mag"]
LABEL_COL    = "Activity"
SUBJECT_COL  = "subject"

K_RANGE      = range(2, 16)   # k=2..15
SEED         = 42

# COMMAND ----------
# MAGIC %md ## 1. Load feature data once (Bug fix: no re-reads in loop)

df = spark.read.format("delta").load(FEATURE_DELTA_PATH).cache()
print(f"Loaded {df.count():,} rows, cached ✓")

evaluator = ClusteringEvaluator(featuresCol="features", metricName="silhouette")

# COMMAND ----------
# MAGIC %md ## 2. Elbow + silhouette sweep across 3 algorithms

mlflow.set_experiment("/mobile-health-sensor-segmentation")

ALGORITHMS = {
    "KMeans":          lambda k: KMeans(k=k, seed=SEED, featuresCol="features"),
    "BisectingKMeans": lambda k: BisectingKMeans(k=k, seed=SEED, featuresCol="features"),
    "GaussianMixture": lambda k: GaussianMixture(k=k, seed=SEED, featuresCol="features"),
}

results = []   # {algo, k, silhouette, wssse}
best    = {"silhouette": -1}

for algo_name, algo_fn in ALGORITHMS.items():
    sils, wssses = [], []
    print(f"\n--- {algo_name} ---")
    for k in K_RANGE:
        with mlflow.start_run(run_name=f"{algo_name}_k{k}"):
            model   = algo_fn(k).fit(df)
            preds   = model.transform(df)
            sil     = evaluator.evaluate(preds)
            # WSSSE only available for KMeans / BisectingKMeans
            wssse   = model.summary.trainingCost if hasattr(model, "summary") else None

            mlflow.log_param("algorithm", algo_name)
            mlflow.log_param("k",         k)
            mlflow.log_metric("silhouette", sil)
            if wssse:
                mlflow.log_metric("wssse", wssse)

            row = {"algo": algo_name, "k": k, "silhouette": round(sil, 4)}
            if wssse:
                row["wssse"] = round(wssse, 2)
            results.append(row)

            print(f"  k={k:2d}  sil={sil:.4f}" + (f"  wssse={wssse:,.0f}" if wssse else ""))

            if algo_name == "KMeans":
                sils.append(sil)
                wssses.append(wssse)

# Find optimal k via elbow method (largest second derivative of WSSSE curve)
kmeans_results = [(r["k"], r["wssse"]) for r in results if r["algo"] == "KMeans" and "wssse" in r]
kmeans_results.sort()
ws = [w for _, w in kmeans_results]
# Second differences: acceleration of WSSSE decrease
diffs2 = [ws[i-1] - 2*ws[i] + ws[i+1] for i in range(1, len(ws)-1)]
elbow_idx = diffs2.index(max(diffs2)) + 1  # +1 because diffs2 starts at index 1
optimal_k = kmeans_results[elbow_idx][0]
print(f"\nElbow method: optimal k={optimal_k}")

# Re-fit with optimal k
optimal_model = KMeans(k=optimal_k, seed=SEED, featuresCol="features").fit(df)
optimal_preds = optimal_model.transform(df)
optimal_sil   = evaluator.evaluate(optimal_preds)
best = {"algo": "KMeans", "k": optimal_k, "silhouette": optimal_sil,
        "model": optimal_model, "preds": optimal_preds}
print(f"Best KMeans: k={best['k']}  silhouette={best['silhouette']:.4f}")

# COMMAND ----------
# MAGIC %md ## 3. Save best model

best["model"].write().overwrite().save(MODEL_SAVE_PATH)
print(f"KMeans model saved to {MODEL_SAVE_PATH} ✓")

# COMMAND ----------
# MAGIC %md ## 4. Write clustered Delta table

df_clustered = best["preds"].select(
    FEATURE_COLS + [LABEL_COL, SUBJECT_COL, "prediction"]
)

(
    df_clustered
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .save(CLUSTERED_PATH)
)
print(f"Clustered data written to {CLUSTERED_PATH} ✓")

# COMMAND ----------
# MAGIC %md ## 5. Build cluster_stats.json (Bug fix: raw-unit means, not empty)

stats = {}
for cluster_id in range(best["k"]):
    subset = df_clustered.filter(F.col("prediction") == cluster_id)
    n      = subset.count()
    means  = subset.select([F.mean(c).alias(c) for c in FEATURE_COLS]).collect()[0].asDict()
    # Activity distribution within this cluster
    act_dist = (
        subset
        .groupBy(LABEL_COL)
        .count()
        .orderBy(F.col("count").desc())
        .collect()
    )
    stats[str(cluster_id)] = {
        "cluster_id":    cluster_id,
        "size":          n,
        "pct":           round(n / df_clustered.count() * 100, 2),
        "feature_means": {k: round(v, 6) for k, v in means.items()},
        "top_activities": [
            {"activity": int(r[LABEL_COL]), "count": int(r["count"])}
            for r in act_dist[:5]
        ],
    }

with open(STATS_JSON_PATH, "w") as f:
    json.dump(stats, f, indent=2)
print(f"cluster_stats.json written ({best['k']} clusters) ✓")

# COMMAND ----------
# MAGIC %md ## 6. Export experiment_results.json for UI

with open(EXPERIMENT_JSON, "w") as f:
    json.dump(results, f, indent=2)
print(f"experiment_results.json written ✓")

# COMMAND ----------

# Activity × cluster cross-tabulation
display(df_clustered.crosstab("prediction", LABEL_COL))

# COMMAND ----------

df.unpersist()
print("clustering COMPLETE ✓")
