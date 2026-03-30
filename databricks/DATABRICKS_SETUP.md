# Databricks Setup Guide

The `setup.py` script handles everything automatically — uploading the dataset,
creating notebooks, running the pipeline, and downloading the results.

You only need to do **two things**:

---

## 1. Get your personal access token

1. In the Databricks UI, click your **avatar (top-right)** → **Settings**
2. Click **Developer** → **Access tokens** → **Generate new token**
3. Give it any name, click **Generate**, and copy the token

---

## 2. Run the setup script

```bash
pip install requests
set DATABRICKS_HOST=https://<your-workspace>.azuredatabricks.net
set DATABRICKS_TOKEN=<paste-token-here>
python databricks/setup.py
```

The script will:
- Upload `mobile_health.csv` to Databricks (153 MB, shows progress)
- Import all 6 notebooks into your workspace
- Create a cluster automatically (or reuse one if already running)
- Run each notebook in order, waiting for each to finish
- Download the 6 JSON result files into `artifacts/`

When it finishes, start the backend:
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Finding your workspace URL

It's the URL you see in your browser when logged into Databricks, e.g.:
`https://adb-1234567890.12.azuredatabricks.net`
