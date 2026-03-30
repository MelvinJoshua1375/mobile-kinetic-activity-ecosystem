/**
 * ExperimentTracker
 *
 * Visualises the elbow curve (WSSSE) and silhouette scores for all
 * algorithm × k combinations from the Databricks sweep.
 */

import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { api, ExperimentRun, ExperimentsResponse } from "../api";

const ALGO_COLOURS: Record<string, string> = {
  KMeans:          "#6366f1",
  BisectingKMeans: "#22d3ee",
  GaussianMixture: "#f59e0b",
};

export default function ExperimentTracker() {
  const [data, setData]     = useState<ExperimentsResponse | null>(null);
  const [algo, setAlgo]     = useState<string>("all");
  const [error, setError]   = useState<string | null>(null);

  useEffect(() => {
    api.experiments(algo === "all" ? undefined : algo)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [algo]);

  if (error) return <div className="text-red-400 p-4">Error: {error}</div>;
  if (!data)  return <div className="text-gray-400 p-4">Loading experiments…</div>;

  const algos = [...new Set(data.runs.map((r) => r.algo))];

  // Group by algorithm for multi-trace plots
  const tracesBySil = algos.map((a) => {
    const runs = data.runs.filter((r) => r.algo === a).sort((a, b) => a.k - b.k);
    return {
      type: "scatter" as const,
      mode: "lines+markers" as const,
      name: a,
      x: runs.map((r) => r.k),
      y: runs.map((r) => r.silhouette),
      line: { color: ALGO_COLOURS[a] ?? "#6b7280" },
      marker: { color: ALGO_COLOURS[a] ?? "#6b7280", size: 6 },
    };
  });

  const kmeansRuns = data.runs.filter((r) => r.algo === "KMeans" && r.wssse != null).sort((a, b) => a.k - b.k);
  const elbowTrace = {
    type: "scatter" as const,
    mode: "lines+markers" as const,
    name: "KMeans WSSSE",
    x: kmeansRuns.map((r) => r.k),
    y: kmeansRuns.map((r) => r.wssse!),
    line: { color: "#6366f1" },
    marker: { color: "#6366f1", size: 6 },
  };

  const layoutBase = {
    paper_bgcolor: "transparent",
    plot_bgcolor:  "transparent",
    font:    { color: "#e5e7eb" },
    xaxis:   { title: "k (clusters)", color: "#9ca3af", dtick: 1 },
    margin:  { t: 20, b: 50, l: 70, r: 20 },
    height:  280,
    legend:  { bgcolor: "transparent" },
  };

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">Experiment Tracker</h2>

      {/* Best run banner */}
      <div className="bg-indigo-900/30 border border-indigo-700 rounded-xl p-4">
        <p className="text-xs text-indigo-300 uppercase tracking-wide">Best Model</p>
        <p className="text-white font-semibold text-lg mt-1">
          {data.best_run.algo} — k={data.best_run.k}
        </p>
        <p className="text-indigo-300 text-sm">
          Silhouette = {data.best_run.silhouette.toFixed(4)}
          {data.best_run.wssse ? `  ·  WSSSE = ${data.best_run.wssse.toLocaleString()}` : ""}
        </p>
      </div>

      {/* Algorithm filter */}
      <div className="flex flex-wrap gap-2">
        {["all", ...algos].map((a) => (
          <button
            key={a}
            onClick={() => setAlgo(a)}
            className={`px-3 py-1 rounded-full text-sm transition-colors ${
              algo === a
                ? "bg-indigo-600 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            {a === "all" ? "All Algorithms" : a}
          </button>
        ))}
      </div>

      {/* Silhouette scores */}
      <div className="bg-gray-800 rounded-xl p-4">
        <p className="text-xs text-gray-500 mb-2">Silhouette Score (higher is better)</p>
        <Plot
          data={tracesBySil}
          layout={{ ...layoutBase, yaxis: { title: "Silhouette", color: "#9ca3af" } }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </div>

      {/* Elbow curve */}
      {kmeansRuns.length > 0 && (
        <div className="bg-gray-800 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-2">KMeans Elbow Curve — WSSSE (lower is better)</p>
          <Plot
            data={[elbowTrace]}
            layout={{ ...layoutBase, yaxis: { title: "WSSSE", color: "#9ca3af" } }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: "100%" }}
          />
        </div>
      )}

      {/* Results table */}
      <div className="bg-gray-800 rounded-xl overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead>
            <tr className="text-gray-500 border-b border-gray-700 text-xs uppercase tracking-wide">
              <th className="px-4 py-3">Algorithm</th>
              <th className="px-4 py-3">k</th>
              <th className="px-4 py-3">Silhouette</th>
              <th className="px-4 py-3">WSSSE</th>
            </tr>
          </thead>
          <tbody>
            {data.runs
              .sort((a, b) => b.silhouette - a.silhouette)
              .map((run, i) => (
                <tr
                  key={i}
                  className={`border-b border-gray-700 text-gray-300 ${
                    run.algo === data.best_run.algo && run.k === data.best_run.k
                      ? "bg-indigo-900/20"
                      : ""
                  }`}
                >
                  <td className="px-4 py-2">
                    <span
                      className="inline-block w-2 h-2 rounded-full mr-2"
                      style={{ backgroundColor: ALGO_COLOURS[run.algo] ?? "#6b7280" }}
                    />
                    {run.algo}
                  </td>
                  <td className="px-4 py-2">{run.k}</td>
                  <td className="px-4 py-2">{run.silhouette.toFixed(4)}</td>
                  <td className="px-4 py-2 text-gray-500">
                    {run.wssse ? run.wssse.toLocaleString() : "—"}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
