"use client";

import { useEffect, useState, useRef } from "react";
import { getPipelineHistory, getPipelineStatus, runPipeline } from "@/lib/api";
import StatusBadge from "@/components/status-badge";

interface PipelineStep {
  status: string;
  count?: number;
  topics?: number;
  opportunities?: number;
}

export default function PipelinePage() {
  const [history, setHistory] = useState<any[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");

  // Live progress polling
  const [activePipelineId, setActivePipelineId] = useState<string | null>(null);
  const [liveStatus, setLiveStatus] = useState<any>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Config
  const [platforms, setPlatforms] = useState(["reddit", "itchio"]);
  const [tiers, setTiers] = useState([1, 2]);
  const [autoApprove, setAutoApprove] = useState(false);

  useEffect(() => {
    load();
  }, []);

  // Polling effect for live pipeline progress
  useEffect(() => {
    if (!activePipelineId) return;

    const poll = async () => {
      try {
        const status = await getPipelineStatus(activePipelineId);
        setLiveStatus(status);
        if (status.status === "completed" || status.status === "failed") {
          // Stop polling
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          setRunning(false);
          if (status.status === "completed") {
            setMessage(`Pipeline completed: ${status.posts_scraped} scraped, ${status.contents_generated} generated`);
          } else {
            setMessage(`Pipeline failed: ${status.error || "Unknown error"}`);
          }
          load();
        }
      } catch {
        // Continue polling on transient errors
      }
    };

    // Poll immediately, then every 3 seconds
    poll();
    intervalRef.current = setInterval(poll, 3000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [activePipelineId]);

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
    setLiveStatus(null);
    try {
      const result = await runPipeline({
        platforms,
        tiers,
        auto_approve: autoApprove,
      });
      setMessage(result.message);
      // Start polling with the returned pipeline_id
      if (result.pipeline_id) {
        setActivePipelineId(result.pipeline_id);
      } else {
        setRunning(false);
        load();
      }
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
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

  function renderStepIcon(step: PipelineStep | undefined) {
    if (!step) return <span className="text-zinc-600">--</span>;
    if (step.status === "completed") {
      return <span className="text-green-400 text-lg">&#10003;</span>;
    }
    if (step.status === "running") {
      return (
        <span className="inline-block w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      );
    }
    if (step.status === "failed") {
      return <span className="text-red-400 text-lg">&#10007;</span>;
    }
    return <span className="text-zinc-600 text-lg">&#9711;</span>;
  }

  function renderStepLabel(name: string, step: PipelineStep | undefined) {
    if (!step) return null;
    if (name === "scrape" && step.count !== undefined) {
      return <span className="text-xs text-zinc-400">{step.count} posts scraped</span>;
    }
    if (name === "analyze") {
      if (step.topics !== undefined) {
        return <span className="text-xs text-zinc-400">{step.topics} topics found</span>;
      }
    }
    if (name === "generate" && step.count !== undefined) {
      return <span className="text-xs text-zinc-400">{step.count} contents generated</span>;
    }
    return null;
  }

  const pipelineStepNames = ["scrape", "analyze", "generate"];

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
          <div
            className={`text-sm rounded px-3 py-2 ${
              message.startsWith("Error") || message.includes("failed")
                ? "text-red-300 bg-red-900/30 border border-red-800"
                : "text-zinc-400 bg-zinc-800"
            }`}
          >
            {message}
          </div>
        )}
      </div>

      {/* Live Progress */}
      {liveStatus && activePipelineId && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Live Progress</h2>
            <StatusBadge status={liveStatus.status} />
          </div>
          {liveStatus.error && (
            <div className="text-sm text-red-400 bg-red-900/20 border border-red-800 rounded px-3 py-2 mb-4">
              {liveStatus.error}
            </div>
          )}
          <div className="flex items-start gap-0">
            {pipelineStepNames.map((name, idx) => {
              const step = liveStatus.steps?.[name] as PipelineStep | undefined;
              return (
                <div key={name} className="flex items-center">
                  <div className="flex flex-col items-center gap-1 min-w-[140px]">
                    <div className="flex items-center justify-center w-10 h-10 rounded-full border-2 border-zinc-700 bg-zinc-800">
                      {renderStepIcon(step)}
                    </div>
                    <span className="text-sm font-medium capitalize">{name}</span>
                    {renderStepLabel(name, step)}
                  </div>
                  {idx < pipelineStepNames.length - 1 && (
                    <div className="w-12 h-0.5 bg-zinc-700 mt-5 -mx-2" />
                  )}
                </div>
              );
            })}
          </div>
          {/* Summary counts */}
          <div className="flex gap-6 mt-4 pt-4 border-t border-zinc-800">
            <div className="text-sm">
              <span className="text-zinc-500">Scraped: </span>
              <span className="text-white font-medium">{liveStatus.posts_scraped ?? 0}</span>
            </div>
            <div className="text-sm">
              <span className="text-zinc-500">Generated: </span>
              <span className="text-white font-medium">{liveStatus.contents_generated ?? 0}</span>
            </div>
          </div>
        </div>
      )}

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
