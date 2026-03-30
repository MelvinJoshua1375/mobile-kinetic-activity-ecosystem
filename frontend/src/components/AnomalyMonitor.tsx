/**
 * AnomalyMonitor
 *
 * Paginated table of anomaly records with filtering by cluster,
 * activity, and minimum anomaly score.  Score is visualised as a
 * colour-coded progress bar.
 */

import { useEffect, useState } from "react";
import { api, AnomalyRecord, AnomaliesResponse } from "../api";

export default function AnomalyMonitor() {
  const [data, setData]         = useState<AnomaliesResponse | null>(null);
  const [page, setPage]         = useState(1);
  const [cluster, setCluster]   = useState<string>("");
  const [activity, setActivity] = useState<string>("");
  const [minScore, setMinScore] = useState<string>("0");
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);

  const PAGE_SIZE = 20;

  useEffect(() => {
    setLoading(true);
    api.anomalies({
      page,
      page_size: PAGE_SIZE,
      cluster:   cluster  ? parseInt(cluster)  : undefined,
      activity:  activity ? parseInt(activity) : undefined,
      min_score: parseFloat(minScore) || 0,
    })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [page, cluster, activity, minScore]);

  const totalPages = data ? Math.ceil(data.records.length / PAGE_SIZE) : 1;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">Anomaly Monitor</h2>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <FilterInput label="Cluster" value={cluster} onChange={(v) => { setCluster(v); setPage(1); }} placeholder="All" type="number" />
        <FilterInput label="Activity" value={activity} onChange={(v) => { setActivity(v); setPage(1); }} placeholder="All" type="number" />
        <FilterInput label="Min Score" value={minScore} onChange={(v) => { setMinScore(v); setPage(1); }} placeholder="0.0" type="number" step="0.05" min="0" max="1" />
      </div>

      {error   && <div className="text-red-400 text-sm">Error: {error}</div>}
      {loading && <div className="text-gray-400 text-sm">Loading…</div>}

      {data && (
        <>
          <p className="text-sm text-gray-400">
            {data.total_anomalies.toLocaleString()} total anomalies
          </p>

          {/* Table */}
          <div className="overflow-x-auto bg-gray-800 rounded-xl">
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="text-gray-500 border-b border-gray-700 text-xs uppercase tracking-wide">
                  <th className="px-4 py-3">Subject</th>
                  <th className="px-4 py-3">Activity</th>
                  <th className="px-4 py-3">Cluster</th>
                  <th className="px-4 py-3">Anomaly Score</th>
                  <th className="px-4 py-3">ISO</th>
                  <th className="px-4 py-3">LOF</th>
                </tr>
              </thead>
              <tbody>
                {data.records.map((rec, i) => (
                  <AnomalyRow key={i} rec={rec} />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center gap-3 justify-end">
            <button
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1 rounded bg-gray-700 text-gray-300 disabled:opacity-40 hover:bg-gray-600 text-sm"
            >
              ← Prev
            </button>
            <span className="text-gray-400 text-sm">Page {page}</span>
            <button
              disabled={data.records.length < PAGE_SIZE}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1 rounded bg-gray-700 text-gray-300 disabled:opacity-40 hover:bg-gray-600 text-sm"
            >
              Next →
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function AnomalyRow({ rec }: { rec: AnomalyRecord }) {
  const score = rec.anomaly_score;
  const pct   = Math.round(score * 100);
  const colour = score > 0.8 ? "bg-red-500" : score > 0.6 ? "bg-orange-400" : "bg-yellow-400";

  return (
    <tr className="border-b border-gray-700 text-gray-300 hover:bg-gray-750 transition-colors">
      <td className="px-4 py-2">{rec.subject}</td>
      <td className="px-4 py-2">{rec.activity}</td>
      <td className="px-4 py-2">{rec.cluster}</td>
      <td className="px-4 py-2 min-w-[120px]">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-gray-700 rounded-full h-2">
            <div className={`h-2 rounded-full ${colour}`} style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs">{score.toFixed(3)}</span>
        </div>
      </td>
      <td className="px-4 py-2 text-xs text-gray-500">{rec.iso_score.toFixed(4)}</td>
      <td className="px-4 py-2 text-xs text-gray-500">{rec.lof_score.toFixed(4)}</td>
    </tr>
  );
}

function FilterInput({
  label, value, onChange, placeholder, type = "text", step, min, max
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  step?: string;
  min?: string;
  max?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-xs text-gray-500">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        step={step}
        min={min}
        max={max}
        className="bg-gray-700 text-gray-200 rounded px-3 py-1.5 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
    </div>
  );
}
