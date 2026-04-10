"use client";

import { useEffect, useState } from "react";
import { getEscalations, resolveEscalation, dismissEscalation, Escalation } from "@/lib/api";

const levelColors: Record<number, string> = {
  1: "bg-zinc-800 text-zinc-300 border-zinc-600",
  2: "bg-yellow-900/40 text-yellow-300 border-yellow-700",
  3: "bg-orange-900/40 text-orange-300 border-orange-700",
  4: "bg-red-900/40 text-red-300 border-red-700",
  5: "bg-purple-900/40 text-purple-300 border-purple-700",
};

const levelLabels: Record<number, string> = {
  1: "L1 - Info",
  2: "L2 - Warning",
  3: "L3 - Urgent",
  4: "L4 - Critical",
  5: "L5 - Emergency",
};

export default function EscalationsPage() {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("open");
  const [levelFilter, setLevelFilter] = useState<number | undefined>(undefined);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    load();
  }, [statusFilter, levelFilter]);

  async function load() {
    setLoading(true);
    try {
      const data = await getEscalations(statusFilter || undefined, levelFilter);
      setEscalations(data);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
    setLoading(false);
  }

  async function handleResolve(id: number) {
    try {
      await resolveEscalation(id);
      setMessage("Escalation resolved");
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleDismiss(id: number) {
    try {
      await dismissEscalation(id);
      setMessage("Escalation dismissed");
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Escalations</h1>

      {message && (
        <div className="text-sm text-zinc-400 bg-zinc-800 rounded px-3 py-2">
          {message}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4 items-end">
        <div>
          <div className="text-xs text-zinc-400 mb-2">Status</div>
          <div className="flex gap-2">
            {["", "open", "resolved", "dismissed"].map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${
                  statusFilter === s
                    ? "bg-zinc-700 text-white"
                    : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
                }`}
              >
                {s || "All"}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="text-xs text-zinc-400 mb-2">Level</div>
          <div className="flex gap-2">
            <button
              onClick={() => setLevelFilter(undefined)}
              className={`px-3 py-1.5 text-sm rounded transition-colors ${
                levelFilter === undefined
                  ? "bg-zinc-700 text-white"
                  : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
              }`}
            >
              All
            </button>
            {[1, 2, 3, 4, 5].map((l) => (
              <button
                key={l}
                onClick={() => setLevelFilter(l)}
                className={`w-8 h-8 text-sm rounded border transition-colors ${
                  levelFilter === l
                    ? "bg-zinc-700 border-zinc-600 text-white"
                    : "bg-zinc-900 border-zinc-800 text-zinc-500"
                }`}
              >
                L{l}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Escalation List */}
      {loading ? (
        <div className="text-zinc-500 py-8 text-center">Loading...</div>
      ) : escalations.length === 0 ? (
        <div className="text-zinc-500 py-8 text-center">No escalations found</div>
      ) : (
        <div className="space-y-3">
          {escalations.map((esc) => {
            const colorClass = levelColors[esc.level] || levelColors[1];
            return (
              <div
                key={esc.id}
                className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden"
              >
                <div className="flex items-center gap-3 px-4 py-3">
                  <span
                    className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${colorClass}`}
                  >
                    {levelLabels[esc.level] || `L${esc.level}`}
                  </span>
                  <span className="text-xs text-zinc-500 font-mono">
                    {esc.trigger_type}
                  </span>
                  <span className="text-sm text-zinc-300 truncate flex-1">
                    {esc.description}
                  </span>
                  <span className="text-xs text-zinc-600">
                    {new Date(esc.created_at).toLocaleString()}
                  </span>
                  <div className="flex gap-2 ml-auto">
                    <button
                      onClick={() => setExpanded(expanded === esc.id ? null : esc.id)}
                      className="px-2 py-1 text-xs border border-zinc-600 text-zinc-300 hover:bg-zinc-700 hover:text-white rounded transition-colors"
                    >
                      {expanded === esc.id ? "Collapse" : "Expand"}
                    </button>
                    {esc.status === "open" && (
                      <>
                        <button
                          onClick={() => handleResolve(esc.id)}
                          className="px-2 py-1 text-xs bg-green-600 hover:bg-green-500 text-white rounded"
                        >
                          Resolve
                        </button>
                        <button
                          onClick={() => handleDismiss(esc.id)}
                          className="px-2 py-1 text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
                        >
                          Dismiss
                        </button>
                      </>
                    )}
                    {esc.status !== "open" && (
                      <span
                        className={`inline-block px-2 py-0.5 text-xs font-medium rounded border ${
                          esc.status === "resolved"
                            ? "bg-green-900/50 text-green-300 border-green-700"
                            : "bg-zinc-800 text-zinc-400 border-zinc-700"
                        }`}
                      >
                        {esc.status}
                      </span>
                    )}
                  </div>
                </div>

                {expanded === esc.id && (
                  <div className="border-t border-zinc-800 px-4 py-4 space-y-3">
                    <div>
                      <div className="text-xs text-zinc-500 mb-1">Description</div>
                      <p className="text-sm text-zinc-300">{esc.description}</p>
                    </div>
                    {esc.ai_draft_response && (
                      <div>
                        <div className="text-xs text-zinc-500 mb-1">AI Draft Response</div>
                        <pre className="whitespace-pre-wrap text-sm text-zinc-300 bg-zinc-800/50 border border-zinc-700 rounded p-3 font-sans leading-relaxed">
                          {esc.ai_draft_response}
                        </pre>
                      </div>
                    )}
                    {esc.resolved_at && (
                      <div className="text-xs text-zinc-500">
                        Resolved: {new Date(esc.resolved_at).toLocaleString()}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
