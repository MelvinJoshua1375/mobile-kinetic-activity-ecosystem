# Mobile Kinetic Activity Ecosystem

Industry-grade rewrite of a PySpark K-Means clustering pipeline for mobile health sensor data. Analyzes accelerometer, gyroscope, and rotation sensor data from 10 subjects performing 13 activities.

## Architecture

```
┌─────────────────────────────────────────────┐
│  Databricks Free Edition                    │
│  Notebooks 01–06 (PySpark + MLflow)        │
│  Delta Lake → 6 JSON artifact files        │
└──────────────────┬──────────────────────────┘
                   │ artifacts/
          ┌────────▼────────┐
          │  FastAPI Backend │  (Render)
          │  /api/clusters   │
          │  /api/anomalies  │
          │  /api/predict    │
          │  /api/experiments│
          └────────┬─────────┘
                   │
          ┌────────▼─────────┐
          │  React Frontend   │  (Vercel)
          │  ClusterExplorer  │
          │  AnomalyMonitor   │
          │  LivePredictor    │
          │  ExperimentTracker│
          └───────────────────┘
```

## Bug Fixes vs Original Notebook

| Original Bug | Fix |
|---|---|
| Outlier-cleaned data never used in modelling | `winsorize()` returns df that flows into Pipeline |
| Only 6/12 sensor columns cleaned | All 12 columns winsorized |
| CSV re-read 16× in elbow loop | Delta Lake + `.cache()` before loop |
| Preprocessing pipeline not saved | `pipeline_model.write().overwrite().save()` |
| Flask tables empty (cluster stats not written) | Raw-unit means in `cluster_stats.json` |
| Only KMeans tested | KMeans + BisectingKMeans + GaussianMixture |
| k=2–9 search range | k=2–15 |
| No cross-tabulation | `df.crosstab("prediction", "Activity")` |
| ngrok token in plain text | Removed; use Render for deployment |

## Quick Start

### 1. Run Databricks Notebooks
Upload and run `databricks/notebooks/01_*.py` → `06_*.py` sequentially.
Download the 6 exported JSON files to `artifacts/`.

### 2. Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000/docs
```

Run tests:
```bash
pytest
```

### 3. Frontend (React)
```bash
cd frontend
npm install
cp .env.example .env   # set VITE_API_URL
npm run dev
# → http://localhost:5173
```

Run tests:
```bash
npm test
```

## Deployment

- **Backend → Render**: connect GitHub repo, set `ARTIFACTS_DIR` env var, root dir = `backend/`
- **Frontend → Vercel**: root dir = `frontend/`, set `VITE_API_URL` to Render URL

## Dataset

`mobile_health.csv` — 1.2M rows, 14 columns
- Sensors: accelerometer (al), gyroscope (gl), rotation acceleration (ar), rotation gravity (gr)
- Labels: Activity (0–12), subject (subject1–subject10)
- Activity 0 = ~72% of data (standing still)

## Results

After fixing all bugs:
- Optimal k = 5 (KMeans, silhouette ≈ 0.28+)
- Isolation Forest + LOF anomaly detection on 10% stratified sample
- All experiments tracked in MLflow on Databricks
