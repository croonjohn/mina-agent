"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  getContentQueue,
  approveContent,
  rejectContent,
  batchApprove,
  batchReject,
  publishContent,
  updateContent,
} from "@/lib/api";
import StatusBadge from "@/components/status-badge";

interface ContentItem {
  id: number;
  platform: string;
  target: string;
  content_type: string;
  title: string | null;
  body: string;
  status: string;
  created_at: string;
  source_post_url?: string;
  content_rules?: {
    valid: boolean;
    issues: string[];
  } | null;
  trend_context?: {
    post_title?: string;
    post_url?: string;
    suggested_angle?: string;
    game_title?: string;
    board_url?: string;
    [key: string]: any;
  };
}

export default function ContentPage() {
  return (
    <Suspense fallback={<div className="text-zinc-500 py-8 text-center">Loading...</div>}>
      <ContentPageInner />
    </Suspense>
  );
}

function ContentPageInner() {
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status") || "";
  const [filter, setFilter] = useState(initialStatus);
  const [items, setItems] = useState<ContentItem[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [expanded, setExpanded] = useState<number | null>(null);
  const [editing, setEditing] = useState<{ id: number; body: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, [filter]);

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(t);
  }, [toast]);

  async function load() {
    setLoading(true);
    try {
      const data = await getContentQueue(filter || undefined);
      setItems(data);
    } catch {}
    setLoading(false);
  }

  async function handleApprove(id: number) {
    await approveContent(id);
    load();
  }

  async function handleReject(id: number) {
    await rejectContent(id);
    load();
  }

  async function handlePublish(id: number) {
    try {
      const result = await publishContent(id);
      // Copy content to clipboard
      const text = (result.title ? result.title + "\n\n" : "") + (result.body || "");
      await navigator.clipboard.writeText(text);
      // Open target URL in new tab
      if (result.target_url) {
        window.open(result.target_url, "_blank");
      }
      setToast("Copied to clipboard! Paste it on the opened page.");
      load();
    } catch {
      setToast("Publish failed");
      load();
    }
  }

  async function handleBatchApprove() {
    if (selected.size === 0) return;
    await batchApprove([...selected]);
    setSelected(new Set());
    load();
  }

  async function handleBatchReject() {
    if (selected.size === 0) return;
    await batchReject([...selected]);
    setSelected(new Set());
    load();
  }

  async function handleSaveEdit() {
    if (!editing) return;
    await updateContent(editing.id, { body: editing.body });
    setEditing(null);
    load();
  }

  async function handleCopyToClipboard(item: ContentItem) {
    const text = (item.title ? item.title + "\n\n" : "") + item.body;
    try {
      await navigator.clipboard.writeText(text);
      setToast("Copied to clipboard!");
    } catch {
      setToast("Failed to copy to clipboard");
    }
  }

  function toggleSelect(id: number) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  }

  function toggleSelectAll() {
    if (selected.size === items.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(items.map((i) => i.id)));
    }
  }

  const pendingItems = items.filter((i) => i.status === "pending");

  return (
    <div className="space-y-4">
      {/* Toast notification */}
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-zinc-800 border border-zinc-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm animate-pulse">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Content Queue</h1>
        <div className="flex gap-2">
          {selected.size > 0 && (
            <>
              <button
                onClick={handleBatchApprove}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded"
              >
                Approve ({selected.size})
              </button>
              <button
                onClick={handleBatchReject}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-500 text-white text-sm rounded"
              >
                Reject ({selected.size})
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {["", "pending", "approved", "rejected", "published"].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 text-sm rounded transition-colors ${
              filter === s
                ? "bg-zinc-700 text-white"
                : "bg-zinc-900 text-zinc-400 hover:text-white border border-zinc-800"
            }`}
          >
            {s || "All"}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-zinc-500 py-8 text-center">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-zinc-500 py-8 text-center">No content items</div>
      ) : (
        <div className="space-y-3">
          {pendingItems.length > 1 && !filter && (
            <button
              onClick={toggleSelectAll}
              className="text-xs text-zinc-500 hover:text-zinc-300"
            >
              {selected.size === items.length ? "Deselect all" : "Select all"}
            </button>
          )}
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden"
            >
              {/* Header Row */}
              <div className="flex items-center gap-3 px-4 py-3">
                {item.status === "pending" && (
                  <input
                    type="checkbox"
                    checked={selected.has(item.id)}
                    onChange={() => toggleSelect(item.id)}
                    className="rounded"
                  />
                )}
                <StatusBadge status={item.status} />
                <span className="text-xs text-zinc-500 font-mono">
                  {item.platform}/{item.target}
                </span>
                <span className="text-xs text-zinc-600">
                  {item.content_type}
                </span>
                {item.title && (
                  <span className="text-sm font-medium truncate flex-1">
                    {item.title}
                  </span>
                )}
                <div className="flex gap-2 ml-auto">
                  <button
                    onClick={() =>
                      setExpanded(expanded === item.id ? null : item.id)
                    }
                    className="px-2 py-1 text-xs border border-zinc-600 text-zinc-300 hover:bg-zinc-700 hover:text-white rounded transition-colors"
                  >
                    {expanded === item.id ? "Collapse" : "Expand"}
                  </button>
                  {item.status === "pending" && (
                    <>
                      <button
                        onClick={() => handleApprove(item.id)}
                        className="px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleReject(item.id)}
                        className="px-2 py-1 text-xs bg-red-900 hover:bg-red-800 text-red-300 rounded"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {item.status === "approved" && (
                    <button
                      onClick={() => handlePublish(item.id)}
                      className="px-2 py-1 text-xs bg-green-600 hover:bg-green-500 text-white rounded"
                    >
                      Copy &amp; Open
                    </button>
                  )}
                </div>
              </div>

              {/* Expanded Body */}
              {expanded === item.id && (
                <div className="border-t border-zinc-800 px-4 py-4">
                  {/* itch.io board URL */}
                  {item.platform === "itchio" && item.trend_context?.board_url && (
                    <div className="mb-3">
                      <span className="text-xs text-zinc-500">Target board: </span>
                      <a
                        href={item.trend_context.board_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-400 hover:text-blue-300 underline"
                      >
                        {item.trend_context.board_url}
                      </a>
                    </div>
                  )}
                  {/* Source post context for all content types */}
                  {item.trend_context?.post_title && (
                    <div className="mb-4 bg-zinc-800/50 border border-zinc-700 rounded p-3">
                      <div className="text-xs text-zinc-500 mb-1">
                        {item.content_type === "comment"
                          ? "Replying to:"
                          : item.content_type === "post"
                          ? "Inspired by:"
                          : "Source:"}
                      </div>
                      <div className="text-sm font-medium">{item.trend_context.post_title}</div>
                      {(() => {
                        const url = item.trend_context?.post_url || item.source_post_url;
                        return url && url !== "N/A" ? (
                          <a href={url} target="_blank" rel="noopener noreferrer"
                            className="text-xs text-blue-400 hover:text-blue-300 mt-1 inline-block">
                            {url}
                          </a>
                        ) : null;
                      })()}
                      {item.trend_context.suggested_angle && (
                        <p className="text-xs text-zinc-400 mt-2">
                          Angle: {item.trend_context.suggested_angle}
                        </p>
                      )}
                    </div>
                  )}
                  {/* Game promotion context */}
                  {item.trend_context?.game_title && (
                    <div className="mb-4 bg-zinc-800/50 border border-zinc-700 rounded p-3">
                      <div className="text-xs text-zinc-500 mb-1">Promoting:</div>
                      <div className="text-sm font-medium">{item.trend_context.game_title}</div>
                      {item.trend_context.game_url && (
                        <span className="text-xs text-zinc-400">{item.trend_context.game_url}</span>
                      )}
                    </div>
                  )}
                  {/* Content Rules warnings */}
                  {item.content_rules && !item.content_rules.valid && (
                    <div className="mb-3 bg-yellow-900/30 border border-yellow-700/50 rounded p-3">
                      <div className="text-xs font-semibold text-yellow-400 mb-1">
                        ⚠ Content Rules Issues
                      </div>
                      <ul className="text-xs text-yellow-300/80 space-y-0.5">
                        {item.content_rules.issues
                          .filter((i: string) => !i.startsWith("Auto-replaced"))
                          .map((issue: string, idx: number) => (
                            <li key={idx}>• {issue}</li>
                          ))}
                      </ul>
                    </div>
                  )}
                  {editing?.id === item.id ? (
                    <div className="space-y-2">
                      <textarea
                        value={editing.body}
                        onChange={(e) =>
                          setEditing({ ...editing, body: e.target.value })
                        }
                        rows={10}
                        className="w-full bg-zinc-800 border border-zinc-700 rounded p-3 text-sm font-mono resize-y focus:outline-none focus:border-zinc-500"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={handleSaveEdit}
                          className="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditing(null)}
                          className="px-3 py-1.5 text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 rounded"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <pre className="whitespace-pre-wrap text-sm text-zinc-300 leading-relaxed font-sans">
                        {item.body}
                      </pre>
                      <div className="flex gap-3 mt-3">
                        {(item.status === "pending" ||
                          item.status === "approved") && (
                          <button
                            onClick={() =>
                              setEditing({ id: item.id, body: item.body })
                            }
                            className="text-xs text-zinc-500 hover:text-zinc-300"
                          >
                            Edit
                          </button>
                        )}
                        {item.platform === "itchio" && (
                          <button
                            onClick={() => handleCopyToClipboard(item)}
                            className="text-xs text-zinc-500 hover:text-zinc-300"
                          >
                            Copy to Clipboard
                          </button>
                        )}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
