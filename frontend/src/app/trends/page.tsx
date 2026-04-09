"use client";

import { useEffect, useState } from "react";
import { getLatestTrends } from "@/lib/api";

interface Topic {
  keyword: string;
  description: string;
  relevance_to_verse8: string;
  post_count: number;
}

interface Opportunity {
  post_title: string;
  platform: string;
  source: string;
  opportunity_type: string;
  suggested_angle: string;
}

export default function TrendsPage() {
  const [topics, setTopics] = useState<Topic[]>([]);
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [sentiment, setSentiment] = useState("");
  const [analyzedAt, setAnalyzedAt] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    load();
  }, []);

  async function load() {
    try {
      const data = await getLatestTrends();
      setTopics(data.topics || []);
      setOpportunities(data.opportunities || []);
      setSentiment(data.sentiment_summary || "");
      setAnalyzedAt(data.analyzed_at || "");
    } catch (e: any) {
      setError(e.message);
    }
  }

  const relColor: Record<string, string> = {
    high: "text-green-400",
    medium: "text-yellow-400",
    low: "text-zinc-500",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Trend Analysis</h1>
        {analyzedAt && (
          <span className="text-sm text-zinc-500">
            Last analyzed: {new Date(analyzedAt).toLocaleString()}
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-800 rounded px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* Sentiment */}
      {sentiment && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
          <h2 className="text-sm font-medium text-zinc-400 mb-2">Community Sentiment</h2>
          <p className="text-sm leading-relaxed">{sentiment}</p>
        </div>
      )}

      {/* Topics */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Trending Topics</h2>
        <div className="grid gap-3">
          {topics.map((t, i) => (
            <div
              key={i}
              className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 flex items-start gap-4"
            >
              <div className="text-2xl font-bold text-zinc-600 w-8 text-right shrink-0">
                {t.post_count}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{t.keyword}</span>
                  <span className={`text-xs ${relColor[t.relevance_to_verse8] || "text-zinc-500"}`}>
                    {t.relevance_to_verse8}
                  </span>
                </div>
                <p className="text-sm text-zinc-400 mt-1">{t.description}</p>
              </div>
            </div>
          ))}
          {topics.length === 0 && (
            <div className="text-zinc-500 py-8 text-center">No trend data yet. Run a pipeline first.</div>
          )}
        </div>
      </div>

      {/* Opportunities */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Engagement Opportunities</h2>
        <div className="space-y-3">
          {opportunities.map((o, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-mono text-zinc-500">
                  {o.platform}/{o.source}
                </span>
                <span className="text-xs bg-zinc-800 px-2 py-0.5 rounded text-zinc-400">
                  {o.opportunity_type}
                </span>
              </div>
              <div className="font-medium text-sm">{o.post_title}</div>
              <p className="text-sm text-zinc-400 mt-2">{o.suggested_angle}</p>
            </div>
          ))}
          {opportunities.length === 0 && (
            <div className="text-zinc-500 py-8 text-center">No opportunities found yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}
