"""
Mobile Health Sensor Segmentation — FastAPI Backend
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .artifacts import load_artifacts
from .routers import health, clusters, anomalies, predict, experiments


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load artifacts once at startup
    load_artifacts()
    yield


app = FastAPI(
    title="Mobile Health Sensor Segmentation API",
    version="1.0.0",
    description="Cluster statistics, anomaly detection, and live prediction for mobile health sensor data.",
    lifespan=lifespan,
)

# CORS — allow Vercel frontend + local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",       # Vite dev server
        "http://localhost:3000",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(clusters.router)
app.include_router(anomalies.router)
app.include_router(predict.router)
app.include_router(experiments.router)


@app.get("/")
def root():
    return {"message": "Mobile Health Sensor Segmentation API — see /docs"}
