"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getPipelineHistory, getContentQueue, runPipeline } from "@/lib/api";
import StatusBadge from "@/components/status-badge";

export default function Dashboard() {
  const [history, setHistory] = useState<any[]>([]);
  const [stats, setStats] = useState({ pending: 0, approved: 0, published: 0 });
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const [h, pending, approved, published] = await Promise.all([
        getPipelineHistory(5),
        getContentQueue("pending"),
        getContentQueue("approved"),
        getContentQueue("published"),
      ]);
      setHistory(h);
      setStats({
        pending: pending.length,
        approved: approved.length,
        published: published.length,
      });
    } catch (e: any) {
      setMessage(e.message);
    }
  }

  async function handleRun() {
    setRunning(true);
    setMessage("Pipeline running...");
    try {
      const result = await runPipeline({
        platforms: ["reddit", "itchio"],
        tiers: [1, 2],
      });
      setMessage(result.message);
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded transition-colors"
        >
          {running ? "Running..." : "Run Pipeline"}
        </button>
      </div>

      {message && (
        <div className="bg-zinc-800 border border-zinc-700 rounded px-4 py-3 text-sm">
          {message}
        </div>
      )}

      <div className="grid grid-cols-3 gap-4">
        <Link
          href="/content?status=pending"
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 hover:border-zinc-600 transition-colors"
        >
          <div className="text-3xl font-bold text-yellow-400">{stats.pending}</div>
          <div className="text-sm text-zinc-400 mt-1">Pending Review</div>
        </Link>
        <Link
          href="/content?status=approved"
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 hover:border-zinc-600 transition-colors"
        >
          <div className="text-3xl font-bold text-blue-400">{stats.approved}</div>
          <div className="text-sm text-zinc-400 mt-1">Approved (Queued)</div>
        </Link>
        <Link
          href="/published"
          className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 hover:border-zinc-600 transition-colors"
        >
          <div className="text-3xl font-bold text-green-400">{stats.published}</div>
          <div className="text-sm text-zinc-400 mt-1">Published</div>
        </Link>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Recent Pipeline Runs</h2>
          <Link href="/pipeline" className="text-sm text-zinc-400 hover:text-white">
            View all
          </Link>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400 text-left">
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Scraped</th>
                <th className="px-4 py-3 font-medium">Generated</th>
                <th className="px-4 py-3 font-medium">Started</th>
                <th className="px-4 py-3 font-medium">Duration</th>
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
                return (
                  <tr key={r.pipeline_id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30">
                    <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                    <td className="px-4 py-3">{r.posts_scraped}</td>
                    <td className="px-4 py-3">{r.contents_generated}</td>
                    <td className="px-4 py-3 text-zinc-400">{started?.toLocaleString()}</td>
                    <td className="px-4 py-3 text-zinc-400">{dur}</td>
                  </tr>
                );
              })}
              {history.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">
                    No pipeline runs yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
