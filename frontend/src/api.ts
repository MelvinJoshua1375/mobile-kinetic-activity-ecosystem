/**
 * Typed API client — all calls go through here.
 * Set VITE_API_URL in .env (defaults to localhost:8000 for dev).
 */

const BASE = import.meta.env.VITE_API_URL ?? "";

async function get<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const url = new URL(BASE + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// Types (mirrors backend schemas)
// ---------------------------------------------------------------------------

export interface ClusterDetail {
  cluster_id: number;
  size: number;
  pct: number;
  feature_means: Record<string, number>;
  top_activities: { activity: number; count: number }[];
}

export interface ClustersResponse {
  k: number;
  clusters: ClusterDetail[];
}

export interface AnomalyRecord {
  activity: number;
  subject: string;
  cluster: number;
  anomaly_score: number;
  iso_score: number;
  lof_score: number;
  al_x: number; al_y: number; al_z: number;
  gl_x: number; gl_y: number; gl_z: number;
  ar_x: number; ar_y: number; ar_z: number;
  gr_x: number; gr_y: number; gr_z: number;
  al_mag: number; gl_mag: number; ar_mag: number; gr_mag: number;
}

export interface AnomaliesResponse {
  total_anomalies: number;
  page: number;
  page_size: number;
  records: AnomalyRecord[];
}

export interface SensorReading {
  al_x: number; al_y: number; al_z: number;
  gl_x: number; gl_y: number; gl_z: number;
  ar_x: number; ar_y: number; ar_z: number;
  gr_x: number; gr_y: number; gr_z: number;
}

export interface PredictResponse {
  cluster: number;
  anomaly_score: number;
  is_anomaly: boolean;
  distances_to_centroids: Record<string, number>;
  magnitudes: Record<string, number>;
}

export interface ExperimentRun {
  algo: string;
  k: number;
  silhouette: number;
  wssse?: number;
}

export interface ExperimentsResponse {
  runs: ExperimentRun[];
  best_run: ExperimentRun;
}

export interface HealthResponse {
  status: string;
  artifacts_loaded: boolean;
  artifact_names: string[];
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export const api = {
  health: () => get<HealthResponse>("/api/health"),

  clusters: () => get<ClustersResponse>("/api/clusters"),

  anomalies: (params?: {
    page?: number;
    page_size?: number;
    cluster?: number;
    activity?: number;
    min_score?: number;
  }) => get<AnomaliesResponse>("/api/anomalies", params as Record<string, number>),

  predict: (reading: SensorReading) =>
    post<PredictResponse>("/api/predict", reading),

  experiments: (algo?: string) =>
    get<ExperimentsResponse>("/api/experiments", algo ? { algo } : undefined),
};
