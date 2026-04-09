"use client";

import { useEffect, useState } from "react";
import { getPublishHistory } from "@/lib/api";

interface PublishedPost {
  id: number;
  content_id: number;
  platform: string;
  external_url: string | null;
  score: number;
  comment_count: number;
  published_at: string;
}

export default function PublishedPage() {
  const [posts, setPosts] = useState<PublishedPost[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const data = await getPublishHistory();
      setPosts(data);
    } catch (e: any) {
      setError(e.message);
    }
  }

  const totalScore = posts.reduce((s, p) => s + p.score, 0);
  const totalComments = posts.reduce((s, p) => s + p.comment_count, 0);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Published Posts</h1>

      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <div className="text-3xl font-bold">{posts.length}</div>
          <div className="text-sm text-zinc-400 mt-1">Total Published</div>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <div className="text-3xl font-bold">{totalScore}</div>
          <div className="text-sm text-zinc-400 mt-1">Total Score</div>
        </div>
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <div className="text-3xl font-bold">{totalComments}</div>
          <div className="text-sm text-zinc-400 mt-1">Total Comments</div>
        </div>
      </div>

      {/* Posts Table */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-zinc-400 text-left">
              <th className="px-4 py-3 font-medium">Platform</th>
              <th className="px-4 py-3 font-medium">URL</th>
              <th className="px-4 py-3 font-medium">Score</th>
              <th className="px-4 py-3 font-medium">Comments</th>
              <th className="px-4 py-3 font-medium">Published</th>
            </tr>
          </thead>
          <tbody>
            {posts.map((p) => (
              <tr
                key={p.id}
                className="border-b border-zinc-800/50 hover:bg-zinc-800/30"
              >
                <td className="px-4 py-3">
                  <span className="text-xs font-mono bg-zinc-800 px-2 py-0.5 rounded">
                    {p.platform}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {p.external_url ? (
                    <a
                      href={p.external_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300 truncate block max-w-xs"
                    >
                      {p.external_url}
                    </a>
                  ) : (
                    <span className="text-zinc-600">-</span>
                  )}
                </td>
                <td className="px-4 py-3">{p.score}</td>
                <td className="px-4 py-3">{p.comment_count}</td>
                <td className="px-4 py-3 text-zinc-400">
                  {new Date(p.published_at).toLocaleString()}
                </td>
              </tr>
            ))}
            {posts.length === 0 && (
              <tr>
                <td
                  colSpan={5}
                  className="px-4 py-8 text-center text-zinc-500"
                >
                  No published posts yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
