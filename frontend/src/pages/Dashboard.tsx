/**
 * Dashboard
 *
 * Single-page layout with a tab bar routing between the 4 components.
 */

import { useState } from "react";
import ClusterExplorer   from "../components/ClusterExplorer";
import AnomalyMonitor    from "../components/AnomalyMonitor";
import LivePredictor     from "../components/LivePredictor";
import ExperimentTracker from "../components/ExperimentTracker";

type Tab = "clusters" | "anomalies" | "predict" | "experiments";

const TABS: { id: Tab; label: string }[] = [
  { id: "clusters",    label: "Cluster Explorer" },
  { id: "anomalies",   label: "Anomaly Monitor" },
  { id: "predict",     label: "Live Predictor" },
  { id: "experiments", label: "Experiment Tracker" },
];

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>("clusters");

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-white">Mobile Health Sensor Segmentation</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              PySpark K-Means · Databricks · FastAPI · React
            </p>
          </div>
          <StatusBadge />
        </div>
      </header>

      {/* Tab bar */}
      <nav className="bg-gray-800 border-b border-gray-700 px-6">
        <div className="max-w-7xl mx-auto flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-3 text-sm font-medium transition-colors border-b-2 ${
                tab === t.id
                  ? "border-indigo-500 text-indigo-400"
                  : "border-transparent text-gray-400 hover:text-gray-200"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {tab === "clusters"    && <ClusterExplorer />}
        {tab === "anomalies"   && <AnomalyMonitor />}
        {tab === "predict"     && <LivePredictor />}
        {tab === "experiments" && <ExperimentTracker />}
      </main>
    </div>
  );
}

function StatusBadge() {
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");

  // Fire-and-forget on mount
  import("../api").then(({ api }) =>
    api.health()
      .then((h) => setStatus(h.artifacts_loaded ? "ok" : "error"))
      .catch(() => setStatus("error"))
  );

  const colours = {
    loading: "bg-gray-600",
    ok:      "bg-green-500",
    error:   "bg-red-500",
  };
  const labels = { loading: "Connecting…", ok: "API Online", error: "API Offline" };

  return (
    <div className="flex items-center gap-2">
      <span className={`w-2 h-2 rounded-full ${colours[status]}`} />
      <span className="text-xs text-gray-400">{labels[status]}</span>
    </div>
  );
}
