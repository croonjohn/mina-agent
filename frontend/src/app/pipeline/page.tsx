"use client";

import { useEffect, useState } from "react";
import { getPipelineHistory, getPipelineStatus, runPipeline } from "@/lib/api";
import StatusBadge from "@/components/status-badge";

export default function PipelinePage() {
  const [history, setHistory] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");

  // Config
  const [platforms, setPlatforms] = useState(["reddit", "itchio"]);
  const [tiers, setTiers] = useState([1, 2]);
  const [autoApprove, setAutoApprove] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const h = await getPipelineHistory(20);
      setHistory(h);
    } catch (e: any) {
      setMessage(e.message);
    }
  }

  async function handleRun() {
    setRunning(true);
    setMessage("");
    try {
      const result = await runPipeline({
        platforms,
        tiers,
        auto_approve: autoApprove,
      });
      setMessage(result.message);
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  async function toggleDetail(id: string) {
    if (expanded === id) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(id);
    try {
      const d = await getPipelineStatus(id);
      setDetail(d);
    } catch {}
  }

  function toggleTier(t: number) {
    setTiers((prev) =>
      prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t].sort()
    );
  }

  function togglePlatform(p: string) {
    setPlatforms((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Pipeline</h1>

      {/* Run Config */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Run Configuration</h2>
        <div className="flex gap-6">
          <div>
            <div className="text-xs text-zinc-400 mb-2">Platforms</div>
            <div className="flex gap-2">
              {["reddit", "itchio"].map((p) => (
                <button
                  key={p}
                  onClick={() => togglePlatform(p)}
                  className={`px-3 py-1.5 text-sm rounded border transition-colors ${
                    platforms.includes(p)
                      ? "bg-zinc-700 border-zinc-600 text-white"
                      : "bg-zinc-900 border-zinc-800 text-zinc-500"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-400 mb-2">Subreddit Tiers</div>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((t) => (
                <button
                  key={t}
                  onClick={() => toggleTier(t)}
                  className={`w-8 h-8 text-sm rounded border transition-colors ${
                    tiers.includes(t)
                      ? "bg-zinc-700 border-zinc-600 text-white"
                      : "bg-zinc-900 border-zinc-800 text-zinc-500"
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs text-zinc-400 mb-2">Options</div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={autoApprove}
                onChange={(e) => setAutoApprove(e.target.checked)}
                className="rounded"
              />
              Auto-approve generated content
            </label>
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={running || platforms.length === 0}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded transition-colors"
        >
          {running ? "Running..." : "Run Pipeline"}
        </button>
        {message && (
          <div className="text-sm text-zinc-400 bg-zinc-800 rounded px-3 py-2">
            {message}
          </div>
        )}
      </div>

      {/* History */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Run History</h2>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400 text-left">
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Scraped</th>
                <th className="px-4 py-3 font-medium">Generated</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {history.map((r) => {
                const started = r.started_at ? new Date(r.started_at) : null;
                const completed = r.completed_at ? new Date(r.completed_at) : null;
                const dur =
                  started && completed
                    ? `${Math.round((completed.getTime() - started.getTime()) / 1000)}s`
                    : "-";
                const isExpanded = expanded === r.pipeline_id;
                return (
                  <tr key={r.pipeline_id}>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3">{r.posts_scraped}</td>
                    <td className="px-4 py-3">{r.contents_generated}</td>
                    <td className="px-4 py-3 text-zinc-400">
                      {started?.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">{dur}</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => toggleDetail(r.pipeline_id)}
                        className="text-xs text-zinc-500 hover:text-white"
                      >
                        {isExpanded ? "Hide" : "Details"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Detail Panel */}
        {detail && expanded && (
          <div className="mt-3 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
            <h3 className="text-sm font-medium mb-3">
              Pipeline Steps - {detail.pipeline_id?.slice(0, 8)}
            </h3>
            {detail.error && (
              <div className="text-sm text-red-400 mb-3">Error: {detail.error}</div>
            )}
            <div className="grid grid-cols-3 gap-3">
              {Object.entries(detail.steps || {}).map(([name, step]: [string, any]) => (
                <div key={name} className="bg-zinc-800 rounded p-3">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium capitalize">{name}</span>
                    <StatusBadge status={step.status} />
                  </div>
                  {step.count !== undefined && (
                    <div className="text-xs text-zinc-400">Count: {step.count}</div>
                  )}
                  {step.topics !== undefined && (
                    <div className="text-xs text-zinc-400">
                      Topics: {step.topics}, Opportunities: {step.opportunities}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
