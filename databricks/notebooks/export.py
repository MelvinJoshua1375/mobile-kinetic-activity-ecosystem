# Databricks notebook source
# MAGIC %md
# MAGIC # 06 — Export Artifacts
# MAGIC
# MAGIC Downloads all 4 JSON artifacts from DBFS to a local `/dbfs` path where they can
# MAGIC be downloaded via the Databricks UI or REST API.
# MAGIC
# MAGIC Artifacts:
# MAGIC | File | Description |
# MAGIC |------|-------------|
# MAGIC | `cluster_stats.json` | Per-cluster sizes, means, top activities |
# MAGIC | `anomalies.json` | Top 500 anomaly records with scores |
# MAGIC | `anomaly_thresholds.json` | Decision thresholds for inference |
# MAGIC | `centroids.json` | Cluster centroid means for predict endpoint |
# MAGIC | `iqr_bounds.json` | Winsorization bounds for inference pre-processing |
# MAGIC | `experiment_results.json` | Elbow/silhouette sweep results for UI |

# COMMAND ----------

import os, json, shutil

ARTIFACTS = [
    "/dbfs/FileStore/mobile_health/cluster_stats.json",
    "/dbfs/FileStore/mobile_health/anomalies.json",
    "/dbfs/FileStore/mobile_health/anomaly_thresholds.json",
    "/dbfs/FileStore/mobile_health/centroids.json",
    "/dbfs/FileStore/mobile_health/iqr_bounds.json",
    "/dbfs/FileStore/mobile_health/experiment_results.json",
]

EXPORT_DIR = "/dbfs/FileStore/mobile_health/export"
os.makedirs(EXPORT_DIR, exist_ok=True)

for src in ARTIFACTS:
    fname = os.path.basename(src)
    dst   = os.path.join(EXPORT_DIR, fname)
    shutil.copy2(src, dst)

    # Validate JSON
    with open(dst) as f:
        data = json.load(f)
    size = os.path.getsize(dst)
    print(f"✓ {fname:35s}  {size:>8,} bytes")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Download Instructions
# MAGIC
# MAGIC In the Databricks UI:
# MAGIC 1. Go to **Data → DBFS → FileStore/mobile_health/export/**
# MAGIC 2. Download each `.json` file
# MAGIC 3. Place them in your backend `artifacts/` folder:
# MAGIC    ```
# MAGIC    artifacts/
# MAGIC    ├── cluster_stats.json
# MAGIC    ├── anomalies.json
# MAGIC    ├── anomaly_thresholds.json
# MAGIC    ├── centroids.json
# MAGIC    ├── iqr_bounds.json
# MAGIC    └── experiment_results.json
# MAGIC    ```

# COMMAND ----------

print("export COMPLETE ✓")
print(f"\nAll artifacts at: {EXPORT_DIR}")
