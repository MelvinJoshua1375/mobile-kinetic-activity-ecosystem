# -*- coding: utf-8 -*-
"""
Databricks one-shot setup script.

Automates the entire pipeline using Unity Catalog Volumes (works on
workspaces where public DBFS root is disabled):
  1. Discover catalog, create schema + volume
  2. Upload mobile_health.csv to the volume
  3. Import notebooks (paths auto-patched to use the volume)
  4. Create or reuse a cluster
  5. Run notebooks in order, waiting for each to finish
  6. Download the 6 JSON artifact files to artifacts/

Usage:
    pip install requests
    set DATABRICKS_HOST=https://<your-workspace>.cloud.databricks.com
    set DATABRICKS_TOKEN=<your-personal-access-token>
    python databricks/setup.py

How to get your token:
    Databricks UI -> top-right avatar -> Settings -> Developer -> Access tokens
    -> Generate new token -> copy it
"""

import base64
import os
import sys
import time
import pathlib
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HOST  = os.environ.get("DATABRICKS_HOST", "").rstrip("/")
TOKEN = os.environ.get("DATABRICKS_TOKEN", "")

if not HOST:
    HOST = input("Databricks workspace URL: ").strip().rstrip("/")
if not TOKEN:
    TOKEN = input("Personal access token: ").strip()

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

SCRIPT_DIR    = pathlib.Path(__file__).parent
PROJECT_ROOT  = SCRIPT_DIR.parent
NOTEBOOKS_DIR = SCRIPT_DIR / "notebooks"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

# Find the CSV
CSV_PATH = PROJECT_ROOT.parent / "Others" / "mobile_health_sensor_segmentation-main" / "mobile_health.csv"
if not CSV_PATH.exists():
    CSV_PATH = PROJECT_ROOT / "mobile_health.csv"
if not CSV_PATH.exists():
    CSV_PATH = pathlib.Path(input("Path to mobile_health.csv: ").strip())

UC_SCHEMA  = "mobile_health"
UC_VOLUME  = "data"
WS_FOLDER  = "/mobile-health-sensor-segmentation"
CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB chunks

NOTEBOOK_ORDER = [
    "data_ingestion",
    "eda",
    "feature_engineering",
    "clustering",
    "anomaly_detection",
    "export",
]

ARTIFACT_FILES = [
    "cluster_stats.json",
    "anomalies.json",
    "anomaly_thresholds.json",
    "centroids.json",
    "iqr_bounds.json",
    "experiment_results.json",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def api(method: str, path: str, **kwargs):
    url  = f"{HOST}/api/{path}"
    resp = requests.request(method, url, headers=HEADERS, **kwargs)
    if not resp.ok:
        print(f"  ERROR {resp.status_code}: {resp.text[:400]}")
        resp.raise_for_status()
    return resp.json() if resp.text.strip() else {}


def files_api(method: str, vol_path: str, extra_headers: dict | None = None, **kwargs):
    """Unity Catalog Files API — vol_path is relative to /Volumes/cat/schema/vol/"""
    url  = f"{HOST}/api/2.0/fs/files/{vol_path}"
    hdrs = {**HEADERS, **(extra_headers or {})}
    resp = requests.request(method, url, headers=hdrs, **kwargs)
    if not resp.ok:
        print(f"  ERROR {resp.status_code}: {resp.text[:400]}")
        resp.raise_for_status()
    return resp


def step(msg: str):
    print(f"\n{'-' * 60}")
    print(f"  {msg}")
    print(f"{'-' * 60}")


# ---------------------------------------------------------------------------
# Step 1 — Discover catalog, create schema + volume
# ---------------------------------------------------------------------------

def setup_volume() -> str:
    """Returns the catalog name used."""
    step("Setting up Unity Catalog volume")

    catalogs   = api("GET", "2.1/unity-catalog/catalogs").get("catalogs", [])
    SKIP       = {"system", "samples", "__databricks_internal"}
    user_cats  = [c["name"] for c in catalogs if c["name"] not in SKIP]

    # Prefer 'workspace' (always exists), then any other user catalog
    if "workspace" in user_cats:
        catalog = "workspace"
    elif user_cats:
        catalog = user_cats[0]
    else:
        sys.exit("  No writable catalogs found.")

    print(f"  Using catalog: {catalog}")

    # Create schema (ignore if already exists)
    r = requests.post(f"{HOST}/api/2.1/unity-catalog/schemas",
                      headers=HEADERS,
                      json={"name": UC_SCHEMA, "catalog_name": catalog})
    if r.status_code == 200:
        print(f"  Created schema: {catalog}.{UC_SCHEMA}")
    elif "ALREADY_EXISTS" in r.text or r.status_code == 409:
        print(f"  Schema {catalog}.{UC_SCHEMA} already exists  OK")
    else:
        print(f"  Schema warning: {r.text[:200]}")

    # Create volume (ignore if already exists)
    r = requests.post(f"{HOST}/api/2.1/unity-catalog/volumes",
                      headers=HEADERS,
                      json={"name": UC_VOLUME, "catalog_name": catalog,
                            "schema_name": UC_SCHEMA, "volume_type": "MANAGED"})
    if r.status_code == 200:
        print(f"  Created volume: {catalog}.{UC_SCHEMA}.{UC_VOLUME}")
    elif "ALREADY_EXISTS" in r.text or r.status_code == 409:
        print(f"  Volume {catalog}.{UC_SCHEMA}.{UC_VOLUME} already exists  OK")
    else:
        print(f"  Volume warning: {r.text[:200]}")

    return catalog


# ---------------------------------------------------------------------------
# Step 2 — Upload CSV to volume
# ---------------------------------------------------------------------------

def upload_csv(catalog: str):
    total = CSV_PATH.stat().st_size
    step(f"Uploading {CSV_PATH.name}  ({total / 1_048_576:.1f} MB)")

    vol_path = f"Volumes/{catalog}/{UC_SCHEMA}/{UC_VOLUME}/mobile_health.csv"

    with open(CSV_PATH, "rb") as f:
        data = f.read()

    # Files API accepts the whole file in one PUT (no size limit documented)
    files_api("PUT", vol_path,
              extra_headers={"Content-Type": "application/octet-stream"},
              data=data)

    print(f"  Uploaded to /Volumes/{catalog}/{UC_SCHEMA}/{UC_VOLUME}/mobile_health.csv  OK")


# ---------------------------------------------------------------------------
# Step 3 — Import notebooks (patch paths to use volume)
# ---------------------------------------------------------------------------

def import_notebooks(catalog: str):
    step("Importing notebooks to Databricks workspace")

    vol_base   = f"/Volumes/{catalog}/{UC_SCHEMA}/{UC_VOLUME}"
    local_base = f"/Volumes/{catalog}/{UC_SCHEMA}/{UC_VOLUME}"

    # Path substitutions: old DBFS paths -> Volume paths
    substitutions = {
        "dbfs:/FileStore/mobile_health/mobile_health.csv": f"{vol_base}/mobile_health.csv",
        "dbfs:/FileStore/mobile_health/delta/raw":         f"{vol_base}/delta/raw",
        "dbfs:/FileStore/mobile_health/delta/features":    f"{vol_base}/delta/features",
        "dbfs:/FileStore/mobile_health/delta/clustered":   f"{vol_base}/delta/clustered",
        "dbfs:/FileStore/mobile_health/pipeline":          f"{vol_base}/pipeline",
        "dbfs:/FileStore/mobile_health/kmeans_model":      f"{vol_base}/kmeans_model",
        "dbfs:/FileStore/mobile_health/export":            f"{vol_base}/export",
        "/dbfs/FileStore/mobile_health/":                  f"{local_base}/",
    }

    try:
        api("POST", "2.0/workspace/mkdirs", json={"path": WS_FOLDER})
    except Exception:
        pass

    for name in NOTEBOOK_ORDER:
        src = NOTEBOOKS_DIR / f"{name}.py"
        if not src.exists():
            print(f"  SKIP {name}.py (not found)")
            continue

        content = src.read_text(encoding="utf-8")
        for old, new in substitutions.items():
            content = content.replace(old, new)

        content_b64 = base64.b64encode(content.encode("utf-8")).decode()
        api("POST", "2.0/workspace/import", json={
            "path":      f"{WS_FOLDER}/{name}",
            "format":    "SOURCE",
            "language":  "PYTHON",
            "content":   content_b64,
            "overwrite": True,
        })
        print(f"  Imported {name}  OK")


# ---------------------------------------------------------------------------
# Step 4 — Resolve compute: prefer serverless, fall back to existing cluster
# ---------------------------------------------------------------------------

def resolve_compute() -> dict:
    """
    Returns the kwargs to pass to runs/submit that specify compute.
    Tries serverless first (no cluster needed), then reuses any running cluster.
    """
    step("Resolving compute")

    # Check for existing running clusters
    clusters = api("GET", "2.0/clusters/list").get("clusters", [])
    running  = [c for c in clusters if c["state"] in ("RUNNING", "RESIZING")]

    if running:
        cid  = running[0]["cluster_id"]
        name = running[0]["cluster_name"]
        print(f"  Found running cluster: {name}  ({cid})")
        return {"existing_cluster_id": cid}

    # Try serverless (queue-based, no cluster required)
    print("  No running cluster found — will use serverless compute")
    return {}   # empty = serverless (Databricks auto-provisions)


# ---------------------------------------------------------------------------
# Step 5 — Run notebooks in order
# ---------------------------------------------------------------------------

def run_notebook(name: str, compute: dict):
    print(f"\n  Submitting: {name}...", flush=True)

    if compute:
        # Classic cluster — single-task format
        payload = {
            "run_name":            f"setup-{name}",
            "existing_cluster_id": compute["existing_cluster_id"],
            "notebook_task":       {"notebook_path": f"{WS_FOLDER}/{name}"},
        }
    else:
        # Serverless — multi-task format required
        payload = {
            "run_name": f"setup-{name}",
            "tasks": [{
                "task_key":      "run",
                "notebook_task": {"notebook_path": f"{WS_FOLDER}/{name}"},
                "environment_key": "env",
            }],
            "environments": [{"environment_key": "env", "spec": {"client": "1"}}],
            "queue": {"enabled": True},
        }

    run    = api("POST", "2.1/jobs/runs/submit", json=payload)
    run_id = run["run_id"]

    for _ in range(300):
        time.sleep(20)
        status = api("GET", f"2.1/jobs/runs/get?run_id={run_id}")
        life   = status["state"]["life_cycle_state"]
        result = status["state"].get("result_state", "")
        print(f"\r  {name}  [{life}]    ", end="", flush=True)

        if life == "TERMINATED":
            if result == "SUCCESS":
                print(f"\r  {name}  DONE                      ")
                return
            msg     = status["state"].get("state_message", "")
            run_url = f"{HOST}/#job/0/run/{run_id}"
            sys.exit(f"\n  {name} FAILED: {result} — {msg}\n  See: {run_url}")

    sys.exit(f"\n  {name} timed out after 100 minutes")


def run_all_notebooks(compute: dict):
    step("Running notebooks in order")
    for name in NOTEBOOK_ORDER:
        run_notebook(name, compute)


# ---------------------------------------------------------------------------
# Step 6 — Download artifacts from volume
# ---------------------------------------------------------------------------

def download_artifacts(catalog: str):
    step("Downloading artifact JSON files")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    for fname in ARTIFACT_FILES:
        vol_path = f"Volumes/{catalog}/{UC_SCHEMA}/{UC_VOLUME}/export/{fname}"
        local    = ARTIFACTS_DIR / fname

        resp = files_api("GET", vol_path)
        local.write_bytes(resp.content)
        print(f"  {fname:35s}  {len(resp.content):>8,} bytes  OK")

    print(f"\n  All artifacts saved to {ARTIFACTS_DIR}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\nDatabricks setup — workspace: {HOST}")

    catalog = setup_volume()
    upload_csv(catalog)
    import_notebooks(catalog)
    compute = resolve_compute()
    run_all_notebooks(compute)
    download_artifacts(catalog)

    print(f"\n{'=' * 60}")
    print("  Setup complete! Next:")
    print("  1. cd backend && pip install -r requirements.txt")
    print("  2. uvicorn app.main:app --reload")
    print(f"{'=' * 60}\n")
