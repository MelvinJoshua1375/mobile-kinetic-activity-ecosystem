"""
Mobile Health Sensor Segmentation — local pipeline.

Produces the same 6 JSON artifacts as the Databricks notebooks but runs
entirely locally using pandas + scikit-learn (no Java / Spark needed).

Usage:
    pip install pandas scikit-learn
    python run_pipeline.py

Artifacts written to artifacts/:
    cluster_stats.json, anomalies.json, anomaly_thresholds.json,
    centroids.json, iqr_bounds.json, experiment_results.json
"""

import json
import math
import pathlib
import sys
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, BisectingKMeans
from sklearn.mixture import GaussianMixture
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import MinMaxScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR    = pathlib.Path(__file__).parent
ARTIFACTS_DIR = SCRIPT_DIR / "artifacts"

CSV_CANDIDATES = [
    SCRIPT_DIR.parent / "Others" / "mobile_health_sensor_segmentation-main" / "mobile_health.csv",
    SCRIPT_DIR / "mobile_health.csv",
]
CSV_PATH = next((p for p in CSV_CANDIDATES if p.exists()), None)
if CSV_PATH is None:
    CSV_PATH = pathlib.Path(input("Path to mobile_health.csv: ").strip())

ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

SENSOR_COLS = ["al_x","al_y","al_z","gl_x","gl_y","gl_z",
               "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z"]
MAG_COLS    = ["al_mag","gl_mag","ar_mag","gr_mag"]
FEATURE_COLS = SENSOR_COLS + MAG_COLS
LABEL_COL   = "Activity"
SUBJECT_COL = "subject"
K_RANGE      = range(2, 16)
TRAIN_SAMPLE = 100_000   # rows used to fit cluster models
SIL_SAMPLE   = 5_000     # rows used for silhouette score (O(n^2))
SEED         = 42


def step(msg):
    print(f"\n{'-' * 60}")
    print(f"  {msg}")
    print(f"{'-' * 60}")


# ---------------------------------------------------------------------------
# 1. Load data
# ---------------------------------------------------------------------------

step(f"Loading {CSV_PATH.name}")
df = pd.read_csv(CSV_PATH)
print(f"  Rows: {len(df):,}  Columns: {list(df.columns)}")

# Normalise column names: alx -> al_x, glx -> gl_x, etc.
rename_map = {}
for col in df.columns:
    if len(col) == 3 and col[:2] in ("al","gl","ar","gr") and col[2] in ("x","y","z"):
        rename_map[col] = f"{col[:2]}_{col[2]}"
if rename_map:
    df = df.rename(columns=rename_map)
    print(f"  Renamed columns: {rename_map}")

for col in SENSOR_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce")
df[LABEL_COL] = pd.to_numeric(df[LABEL_COL], errors="coerce").astype("Int64")
df = df.dropna(subset=SENSOR_COLS + [LABEL_COL])
print(f"  After null drop: {len(df):,} rows")

# Activity distribution
print("\n  Activity distribution:")
dist = df[LABEL_COL].value_counts().sort_index()
for act, cnt in dist.items():
    print(f"    Activity {act:2d}: {cnt:>7,}  ({cnt/len(df)*100:.1f}%)")


# ---------------------------------------------------------------------------
# 2. IQR winsorization — ALL 12 sensor columns
# ---------------------------------------------------------------------------

step("Winsorizing outliers (IQR)")
iqr_bounds = {}
for col in SENSOR_COLS:
    q1  = df[col].quantile(0.25)
    q3  = df[col].quantile(0.75)
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    iqr_bounds[col] = [round(lo, 6), round(hi, 6)]
    df[col] = df[col].clip(lo, hi)
    print(f"  {col:8s}  [{lo:8.3f}, {hi:8.3f}]")

(ARTIFACTS_DIR / "iqr_bounds.json").write_text(json.dumps(iqr_bounds, indent=2))
print("\n  iqr_bounds.json written")


# ---------------------------------------------------------------------------
# 3. Magnitude features
# ---------------------------------------------------------------------------

step("Adding magnitude features")
df["al_mag"] = np.sqrt(df["al_x"]**2 + df["al_y"]**2 + df["al_z"]**2)
df["gl_mag"] = np.sqrt(df["gl_x"]**2 + df["gl_y"]**2 + df["gl_z"]**2)
df["ar_mag"] = np.sqrt(df["ar_x"]**2 + df["ar_y"]**2 + df["ar_z"]**2)
df["gr_mag"] = np.sqrt(df["gr_x"]**2 + df["gr_y"]**2 + df["gr_z"]**2)
print(f"  Features: {FEATURE_COLS}")


# ---------------------------------------------------------------------------
# 4. Scale features
# ---------------------------------------------------------------------------

step("Scaling features (MinMax)")
scaler   = MinMaxScaler()
X_scaled = scaler.fit_transform(df[FEATURE_COLS].values)
print(f"  X_scaled shape: {X_scaled.shape}")


# ---------------------------------------------------------------------------
# 5. Clustering sweep — KMeans, BisectingKMeans, GaussianMixture
# ---------------------------------------------------------------------------

step("Clustering sweep  k=2..15")

results = []
best    = {"silhouette": -1}

# Fixed random subsets reused across all runs to keep comparison fair
rng        = np.random.default_rng(SEED)
train_idx  = rng.choice(len(X_scaled), size=min(TRAIN_SAMPLE, len(X_scaled)), replace=False)
sil_idx    = rng.choice(len(X_scaled), size=min(SIL_SAMPLE,   len(X_scaled)), replace=False)
X_train    = X_scaled[train_idx]
X_sil      = X_scaled[sil_idx]

ALGOS = {
    "KMeans":          lambda k: KMeans(n_clusters=k, random_state=SEED, n_init=5, max_iter=200),
    "BisectingKMeans": lambda k: BisectingKMeans(n_clusters=k, random_state=SEED),
    "GaussianMixture": lambda k: GaussianMixture(n_components=k, random_state=SEED, max_iter=100),
}

for algo_name, algo_fn in ALGOS.items():
    print(f"\n  --- {algo_name} ---")
    for k in K_RANGE:
        t0    = time.time()
        model = algo_fn(k).fit(X_train)

        # Predict on sil sample (all algos support predict)
        sil_labels = model.predict(X_sil)
        sil        = silhouette_score(X_sil, sil_labels)

        inertia = getattr(model, "inertia_", None)
        elapsed = time.time() - t0
        print(f"    k={k:2d}  sil={sil:.4f}" + (f"  inertia={inertia:,.0f}" if inertia else "") + f"  ({elapsed:.1f}s)")

        row = {"algo": algo_name, "k": k, "silhouette": round(sil, 4)}
        if inertia:
            row["wssse"] = round(inertia, 2)
        results.append(row)

        if algo_name == "KMeans" and sil > best["silhouette"]:
            # Store the model; labels will be predicted on full data below
            best = {"algo": algo_name, "k": k, "silhouette": sil, "model": model}

print(f"\n  Best KMeans: k={best['k']}  silhouette={best['silhouette']:.4f}")

(ARTIFACTS_DIR / "experiment_results.json").write_text(json.dumps(results, indent=2))
print("  experiment_results.json written")


# ---------------------------------------------------------------------------
# 6. Assign clusters to full dataset
# ---------------------------------------------------------------------------

step("Assigning cluster labels to full dataset")
print(f"  Predicting with best KMeans k={best['k']} on {len(X_scaled):,} rows...")
df["cluster"] = best["model"].predict(X_scaled)

print("  Cluster sizes:")
for c, cnt in df["cluster"].value_counts().sort_index().items():
    print(f"    Cluster {c}: {cnt:>7,}  ({cnt/len(df)*100:.1f}%)")


# ---------------------------------------------------------------------------
# 7. Build cluster_stats.json
# ---------------------------------------------------------------------------

step("Building cluster statistics")
cluster_stats = {}
k = best["k"]

for cid in range(k):
    subset = df[df["cluster"] == cid]
    n      = len(subset)
    means  = subset[FEATURE_COLS].mean().round(6).to_dict()

    act_dist = (
        subset[LABEL_COL]
        .value_counts()
        .head(5)
        .reset_index()
        .rename(columns={LABEL_COL: "activity", "count": "count"})
    )

    cluster_stats[str(cid)] = {
        "cluster_id":    cid,
        "size":          int(n),
        "pct":           round(n / len(df) * 100, 2),
        "feature_means": {k2: round(float(v), 6) for k2, v in means.items()},
        "top_activities": [
            {"activity": int(r["activity"]), "count": int(r["count"])}
            for _, r in act_dist.iterrows()
        ],
    }
    print(f"  Cluster {cid}: {n:,} rows  ({cluster_stats[str(cid)]['pct']}%)")

(ARTIFACTS_DIR / "cluster_stats.json").write_text(json.dumps(cluster_stats, indent=2))
print("  cluster_stats.json written")


# ---------------------------------------------------------------------------
# 8. Build centroids.json
# ---------------------------------------------------------------------------

centroids = {
    str(cid): stats["feature_means"]
    for cid, stats in cluster_stats.items()
}
(ARTIFACTS_DIR / "centroids.json").write_text(json.dumps(centroids, indent=2))
print("  centroids.json written")


# ---------------------------------------------------------------------------
# 9. Anomaly detection — IsolationForest + LOF on 10% stratified sample
# ---------------------------------------------------------------------------

step("Anomaly detection")

sample_10 = (
    df.groupby(LABEL_COL, group_keys=False)
    .apply(lambda g: g.sample(frac=0.10, random_state=SEED))
)
X_sample = sample_10[FEATURE_COLS].values
print(f"  Training sample: {len(X_sample):,} rows")

iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=SEED, n_jobs=-1)
iso.fit(X_sample)

lof = LocalOutlierFactor(n_neighbors=20, contamination=0.05, novelty=True, n_jobs=-1)
lof.fit(X_sample)

print("  Scoring full dataset...")
X_full       = df[FEATURE_COLS].values
iso_scores   = iso.score_samples(X_full)
lof_scores   = lof.score_samples(X_full)

def minmax_norm(arr):
    lo, hi = arr.min(), arr.max()
    return (arr - lo) / (hi - lo + 1e-9)

combined      = (minmax_norm(iso_scores) + minmax_norm(lof_scores)) / 2
anomaly_score = 1 - combined   # 1 = most anomalous

threshold     = float(np.percentile(anomaly_score, 95))
is_anomaly    = anomaly_score > threshold

df["iso_score"]     = iso_scores
df["lof_score"]     = lof_scores
df["anomaly_score"] = anomaly_score
df["is_anomaly"]    = is_anomaly

n_anomalies = int(is_anomaly.sum())
print(f"  Flagged: {n_anomalies:,} anomalies  ({n_anomalies/len(df)*100:.2f}%)")


# ---------------------------------------------------------------------------
# 10. Build anomalies.json
# ---------------------------------------------------------------------------

step("Building anomaly records")
top = (
    df[df["is_anomaly"]]
    .sort_values("anomaly_score", ascending=False)
    .head(500)
)

float_cols = FEATURE_COLS + ["anomaly_score", "iso_score", "lof_score"]
records    = []
for _, row in top.iterrows():
    rec = {
        "activity":      int(row[LABEL_COL]),
        "subject":       str(row[SUBJECT_COL]),
        "cluster":       int(row["cluster"]),
        "anomaly_score": round(float(row["anomaly_score"]), 6),
        "iso_score":     round(float(row["iso_score"]), 6),
        "lof_score":     round(float(row["lof_score"]), 6),
    }
    for col in FEATURE_COLS:
        rec[col] = round(float(row[col]), 6)
    records.append(rec)

anomalies_out = {"total_anomalies": n_anomalies, "records": records}
(ARTIFACTS_DIR / "anomalies.json").write_text(json.dumps(anomalies_out, indent=2))
print(f"  anomalies.json written ({len(records)} records)")


# ---------------------------------------------------------------------------
# 11. Build anomaly_thresholds.json
# ---------------------------------------------------------------------------

thresholds = {
    "iso_threshold":      round(float(np.percentile(iso_scores,   5)), 6),
    "lof_threshold":      round(float(np.percentile(lof_scores,   5)), 6),
    "combined_threshold": round(float(threshold), 6),
}
(ARTIFACTS_DIR / "anomaly_thresholds.json").write_text(json.dumps(thresholds, indent=2))
print("  anomaly_thresholds.json written")


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

print(f"\n{'=' * 60}")
print("  Pipeline complete! Artifacts written to artifacts/:")
for f in sorted(ARTIFACTS_DIR.glob("*.json")):
    print(f"    {f.name:35s}  {f.stat().st_size:>8,} bytes")
print(f"\n  Now start the backend:")
print("    cd backend && pip install -r requirements.txt")
print("    uvicorn app.main:app --reload")
print(f"{'=' * 60}\n")
