/**
 * LivePredictor
 *
 * Form with 12 sensor inputs → calls POST /api/predict → shows cluster,
 * anomaly score, and distances to centroids.
 */

import { useState } from "react";
import Plot from "react-plotly.js";
import { api, SensorReading, PredictResponse } from "../api";

const SENSOR_GROUPS: { label: string; cols: (keyof SensorReading)[] }[] = [
  { label: "Accelerometer (al)", cols: ["al_x", "al_y", "al_z"] },
  { label: "Gyroscope (gl)",     cols: ["gl_x", "gl_y", "gl_z"] },
  { label: "Rotation Accel (ar)", cols: ["ar_x", "ar_y", "ar_z"] },
  { label: "Rotation Gravity (gr)", cols: ["gr_x", "gr_y", "gr_z"] },
];

const DEFAULTS: SensorReading = {
  al_x: 0.1, al_y: 0.2, al_z: 9.8,
  gl_x: 0.0, gl_y: 0.0, gl_z: 0.0,
  ar_x: 0.0, ar_y: 0.0, ar_z: 0.0,
  gr_x: 0.0, gr_y: 9.8, gr_z: 0.0,
};

export default function LivePredictor() {
  const [values, setValues]   = useState<SensorReading>({ ...DEFAULTS });
  const [result, setResult]   = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const handleChange = (key: keyof SensorReading, val: string) => {
    setValues((prev) => ({ ...prev, [key]: parseFloat(val) || 0 }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.predict(values);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Prediction failed");
    } finally {
      setLoading(false);
    }
  };

  const distLabels = result ? Object.keys(result.distances_to_centroids).map((k) => `Cluster ${k}`) : [];
  const distValues = result ? Object.values(result.distances_to_centroids) : [];

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">Live Predictor</h2>
      <p className="text-sm text-gray-400">
        Enter sensor readings to get real-time cluster assignment and anomaly detection.
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {SENSOR_GROUPS.map((group) => (
            <div key={group.label} className="bg-gray-800 rounded-xl p-4 space-y-3">
              <p className="text-xs font-medium text-gray-400 uppercase tracking-wide">{group.label}</p>
              {group.cols.map((col) => (
                <div key={col} className="flex items-center gap-3">
                  <label className="text-sm text-gray-400 w-12">{col}</label>
                  <input
                    type="number"
                    step="0.001"
                    value={values[col]}
                    onChange={(e) => handleChange(col, e.target.value)}
                    className="flex-1 bg-gray-700 text-gray-200 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              ))}
            </div>
          ))}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full md:w-auto px-8 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors"
        >
          {loading ? "Predicting…" : "Predict Cluster"}
        </button>
      </form>

      {error && <div className="text-red-400 text-sm">Error: {error}</div>}

      {result && (
        <div className="space-y-4">
          {/* Result summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ResultCard label="Assigned Cluster" value={`Cluster ${result.cluster}`} />
            <ResultCard
              label="Anomaly Score"
              value={result.anomaly_score.toFixed(4)}
              highlight={result.anomaly_score > 0.9}
            />
            <ResultCard
              label="Is Anomaly"
              value={result.is_anomaly ? "YES" : "NO"}
              highlight={result.is_anomaly}
            />
            <ResultCard label="al_mag" value={result.magnitudes.al_mag?.toFixed(4) ?? "—"} />
          </div>

          {/* Distances bar chart */}
          <div className="bg-gray-800 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-3">Distance to each cluster centroid (lower = closer)</p>
            <Plot
              data={[{
                type: "bar",
                x: distLabels,
                y: distValues,
                marker: {
                  color: distValues.map((_, i) =>
                    i === result.cluster ? "#6366f1" : "#374151"
                  ),
                },
              }]}
              layout={{
                paper_bgcolor: "transparent",
                plot_bgcolor: "transparent",
                font: { color: "#e5e7eb" },
                xaxis: { color: "#9ca3af" },
                yaxis: { color: "#9ca3af" },
                margin: { t: 20, b: 40, l: 60, r: 20 },
                height: 200,
              }}
              config={{ displayModeBar: false, responsive: true }}
              style={{ width: "100%" }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function ResultCard({
  label, value, highlight = false
}: {
  label: string; value: string; highlight?: boolean;
}) {
  return (
    <div className={`rounded-xl p-4 ${highlight ? "bg-red-900/40 border border-red-700" : "bg-gray-800"}`}>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className={`text-xl font-bold mt-1 ${highlight ? "text-red-400" : "text-white"}`}>{value}</p>
    </div>
  );
}
