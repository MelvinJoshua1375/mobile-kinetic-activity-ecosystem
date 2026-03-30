/**
 * ClusterExplorer
 *
 * Displays per-cluster statistics with a bar chart of feature means
 * and a table of top activities.
 */

import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { api, ClusterDetail, ClustersResponse } from "../api";

const FEATURE_COLS = [
  "al_x","al_y","al_z","gl_x","gl_y","gl_z",
  "ar_x","ar_y","ar_z","gr_x","gr_y","gr_z",
  "al_mag","gl_mag","ar_mag","gr_mag",
];

const CLUSTER_COLOURS = [
  "#6366f1","#22d3ee","#f59e0b","#10b981","#ef4444",
  "#a855f7","#f97316","#14b8a6",
];

export default function ClusterExplorer() {
  const [data, setData] = useState<ClustersResponse | null>(null);
  const [selected, setSelected] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.clusters()
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="text-red-400 p-4">Error: {error}</div>;
  if (!data)  return <div className="text-gray-400 p-4">Loading clusters…</div>;

  const cluster: ClusterDetail = data.clusters[selected];
  const means = FEATURE_COLS.map((f) => cluster.feature_means[f] ?? 0);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">Cluster Explorer</h2>

      {/* Cluster selector */}
      <div className="flex flex-wrap gap-2">
        {data.clusters.map((c) => (
          <button
            key={c.cluster_id}
            onClick={() => setSelected(c.cluster_id)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              selected === c.cluster_id
                ? "bg-indigo-600 text-white"
                : "bg-gray-700 text-gray-300 hover:bg-gray-600"
            }`}
          >
            Cluster {c.cluster_id} ({c.pct.toFixed(1)}%)
          </button>
        ))}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard label="Size" value={cluster.size.toLocaleString()} />
        <StatCard label="Percentage" value={`${cluster.pct.toFixed(2)}%`} />
        <StatCard
          label="Top Activity"
          value={`Activity ${cluster.top_activities[0]?.activity ?? "—"}`}
        />
      </div>

      {/* Feature means bar chart */}
      <div className="bg-gray-800 rounded-xl p-4">
        <Plot
          data={[
            {
              type: "bar",
              x: FEATURE_COLS,
              y: means,
              marker: { color: CLUSTER_COLOURS[selected % CLUSTER_COLOURS.length] },
            },
          ]}
          layout={{
            paper_bgcolor: "transparent",
            plot_bgcolor: "transparent",
            font: { color: "#e5e7eb" },
            xaxis: { tickangle: -45, color: "#9ca3af" },
            yaxis: { color: "#9ca3af" },
            margin: { t: 20, b: 100, l: 60, r: 20 },
            height: 320,
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
        <p className="text-xs text-gray-500 mt-1 text-center">Feature means (raw units after winsorization)</p>
      </div>

      {/* Top activities */}
      <div className="bg-gray-800 rounded-xl p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-3">Top Activities in Cluster</h3>
        <table className="w-full text-sm text-left">
          <thead>
            <tr className="text-gray-500 border-b border-gray-700">
              <th className="pb-2">Activity ID</th>
              <th className="pb-2 text-right">Count</th>
            </tr>
          </thead>
          <tbody>
            {cluster.top_activities.map((a) => (
              <tr key={a.activity} className="border-b border-gray-700 text-gray-300">
                <td className="py-2">Activity {a.activity}</td>
                <td className="py-2 text-right">{a.count.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
