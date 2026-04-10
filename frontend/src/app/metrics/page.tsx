"use client";

import { useEffect, useState } from "react";
import { getMetrics, MetricsSummary } from "@/lib/api";

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [period, setPeriod] = useState("weekly");
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    load();
  }, [period]);

  async function load() {
    setLoading(true);
    try {
      const data = await getMetrics(period);
      setMetrics(data);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
    setLoading(false);
  }

  // Status colors for the content breakdown
  const statusColors: Record<string, string> = {
    pending: "bg-yellow-600",
    approved: "bg-blue-600",
    published: "bg-green-600",
    rejected: "bg-red-600",
    failed: "bg-zinc-600",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Metrics</h1>
        <div className="flex gap-2">
          {["daily", "weekly", "monthly"].map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-sm rounded transition-colors capitalize ${
                period === p
                  ? "bg-zinc-700 text-white"
                  : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {message && (
        <div className="text-sm text-zinc-400 bg-zinc-800 rounded px-3 py-2">
          {message}
        </div>
      )}

      {loading ? (
        <div className="text-zinc-500 py-8 text-center">Loading...</div>
      ) : !metrics ? (
        <div className="text-zinc-500 py-8 text-center">No metrics data available</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <div className="text-3xl font-bold text-green-400">
                {metrics.published.count}
              </div>
              <div className="text-sm text-zinc-400 mt-1">Published</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <div className="text-3xl font-bold text-blue-400">
                {metrics.published.total_score}
              </div>
              <div className="text-sm text-zinc-400 mt-1">Total Score</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <div className="text-3xl font-bold text-purple-400">
                {metrics.published.total_comments}
              </div>
              <div className="text-sm text-zinc-400 mt-1">Total Comments</div>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <div className="text-3xl font-bold text-yellow-400">
                {metrics.pipelines.total_runs}
              </div>
              <div className="text-sm text-zinc-400 mt-1">Pipeline Runs</div>
            </div>
          </div>

          {/* Content Breakdown by Status */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
            <h2 className="font-semibold mb-4">Content Breakdown</h2>
            <div className="space-y-3">
              {Object.entries(metrics.content.by_status).map(([status, count]) => {
                const maxCount = Math.max(
                  ...Object.values(metrics.content.by_status),
                  1
                );
                return (
                  <div key={status} className="flex items-center gap-3">
                    <span className="text-xs text-zinc-400 w-20 shrink-0 capitalize">
                      {status}
                    </span>
                    <div className="flex-1 h-6 bg-zinc-800 rounded overflow-hidden">
                      <div
                        className={`h-full ${statusColors[status] || "bg-zinc-600"} rounded transition-all`}
                        style={{
                          width: `${(count / maxCount) * 100}%`,
                          minWidth: count > 0 ? "8px" : "0",
                        }}
                      />
                    </div>
                    <span className="text-xs text-zinc-300 w-8 text-right">
                      {count}
                    </span>
                  </div>
                );
              })}
              <div className="pt-2 border-t border-zinc-800 text-sm text-zinc-400">
                Total: {metrics.content.total}
              </div>
            </div>
          </div>

          {/* Additional Stats */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <h2 className="font-semibold mb-3">Published Performance</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Avg Score</span>
                  <span className="text-zinc-200">{metrics.published.avg_score.toFixed(1)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Avg Comments</span>
                  <span className="text-zinc-200">{metrics.published.avg_comments.toFixed(1)}</span>
                </div>
              </div>
            </div>
            <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <h2 className="font-semibold mb-3">Escalations</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-zinc-400">Open</span>
                  <span className="text-yellow-400 font-medium">{metrics.escalations.open}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Resolved</span>
                  <span className="text-green-400 font-medium">{metrics.escalations.resolved}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-zinc-400">Total</span>
                  <span className="text-zinc-200">{metrics.escalations.total}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Pipeline Stats */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
            <h2 className="font-semibold mb-3">Pipeline Summary</h2>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-zinc-400">Total Runs</div>
                <div className="text-lg font-medium">{metrics.pipelines.total_runs}</div>
              </div>
              <div>
                <div className="text-zinc-400">Posts Scraped</div>
                <div className="text-lg font-medium">{metrics.pipelines.total_scraped}</div>
              </div>
              <div>
                <div className="text-zinc-400">Contents Generated</div>
                <div className="text-lg font-medium">{metrics.pipelines.total_generated}</div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
