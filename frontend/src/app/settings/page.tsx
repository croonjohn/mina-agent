"use client";

import { useEffect, useState } from "react";
import {
  getSubreddits,
  addSubreddit,
  removeSubreddit,
  getDiscordWebhook,
  updateDiscordWebhook,
  testDiscordWebhook,
  getHealthCheck,
  SubredditConfig,
} from "@/lib/api";

export default function SettingsPage() {
  const [subreddits, setSubreddits] = useState<SubredditConfig[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [discordUrl, setDiscordUrl] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  // Add subreddit form
  const [newSubName, setNewSubName] = useState("");
  const [newSubTier, setNewSubTier] = useState(3);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const [subs, webhook, hp] = await Promise.all([
        getSubreddits().catch(() => []),
        getDiscordWebhook().catch(() => ({ url: "" })),
        getHealthCheck().catch(() => null),
      ]);
      setSubreddits(subs);
      setDiscordUrl(webhook.url || "");
      setHealth(hp);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
    setLoading(false);
  }

  async function handleAddSubreddit() {
    const name = newSubName.trim();
    if (!name) {
      setMessage("Subreddit name is required");
      return;
    }
    try {
      await addSubreddit({ name, tier: newSubTier });
      setNewSubName("");
      setMessage(`Added r/${name} (tier ${newSubTier})`);
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleRemoveSubreddit(name: string) {
    if (!confirm(`Remove r/${name}?`)) return;
    try {
      await removeSubreddit(name);
      setMessage(`Removed r/${name}`);
      load();
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleSaveDiscord() {
    try {
      await updateDiscordWebhook(discordUrl);
      setMessage("Discord webhook URL saved");
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  async function handleTestDiscord() {
    try {
      const result = await testDiscordWebhook();
      setMessage(result.success ? "Test message sent!" : `Test failed: ${result.message}`);
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
  }

  // Group subreddits by tier
  const tiers = [1, 2, 3, 4, 5];
  const subsByTier = tiers.map((tier) => ({
    tier,
    subs: subreddits.filter((s) => s.tier === tier),
  }));

  if (loading) {
    return <div className="text-zinc-500 py-8 text-center">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {message && (
        <div className="text-sm text-zinc-400 bg-zinc-800 rounded px-3 py-2">
          {message}
        </div>
      )}

      {/* Subreddit Management */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Subreddit Management</h2>

        {/* Add form */}
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-zinc-400 mb-1">Subreddit Name</label>
            <input
              type="text"
              value={newSubName}
              onChange={(e) => setNewSubName(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-500"
              placeholder="e.g. gamedev"
            />
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1">Tier</label>
            <select
              value={newSubTier}
              onChange={(e) => setNewSubTier(Number(e.target.value))}
              className="bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-zinc-500"
            >
              {tiers.map((t) => (
                <option key={t} value={t}>
                  Tier {t}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={handleAddSubreddit}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded"
          >
            Add
          </button>
        </div>

        {/* Subreddits by tier */}
        <div className="space-y-3">
          {subsByTier.map(
            ({ tier, subs }) =>
              subs.length > 0 && (
                <div key={tier}>
                  <div className="text-xs text-zinc-400 mb-1">Tier {tier}</div>
                  <div className="flex flex-wrap gap-2">
                    {subs.map((s) => (
                      <span
                        key={s.name}
                        className="inline-flex items-center gap-1 px-3 py-1 bg-zinc-800 border border-zinc-700 text-zinc-300 text-sm rounded"
                      >
                        r/{s.name}
                        <button
                          onClick={() => handleRemoveSubreddit(s.name)}
                          className="text-zinc-500 hover:text-red-400 ml-1"
                        >
                          x
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )
          )}
          {subreddits.length === 0 && (
            <span className="text-zinc-600 text-sm">No subreddits configured</span>
          )}
        </div>
      </div>

      {/* Discord Webhook */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-4">
        <h2 className="font-semibold">Discord Webhook</h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={discordUrl}
            onChange={(e) => setDiscordUrl(e.target.value)}
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded px-3 py-2 text-sm font-mono focus:outline-none focus:border-zinc-500"
            placeholder="https://discord.com/api/webhooks/..."
          />
          <button
            onClick={handleSaveDiscord}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded"
          >
            Save
          </button>
          <button
            onClick={handleTestDiscord}
            className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 text-zinc-200 text-sm rounded border border-zinc-600"
          >
            Test
          </button>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 space-y-3">
        <h2 className="font-semibold">System Info</h2>
        {health ? (
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-zinc-800 rounded p-3">
              <div className="text-xs text-zinc-500">Status</div>
              <div
                className={`text-sm font-medium ${
                  health.status === "healthy" ? "text-green-400" : "text-red-400"
                }`}
              >
                {health.status}
              </div>
            </div>
            <div className="bg-zinc-800 rounded p-3">
              <div className="text-xs text-zinc-500">Version</div>
              <div className="text-sm font-medium">{health.version || "N/A"}</div>
            </div>
            <div className="bg-zinc-800 rounded p-3">
              <div className="text-xs text-zinc-500">Uptime</div>
              <div className="text-sm font-medium">
                {health.uptime || "N/A"}
              </div>
            </div>
            <div className="bg-zinc-800 rounded p-3">
              <div className="text-xs text-zinc-500">Database</div>
              <div
                className={`text-sm font-medium ${
                  health.database === "connected" ? "text-green-400" : "text-red-400"
                }`}
              >
                {health.database || "N/A"}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-zinc-500 text-sm">
            Unable to fetch system health info
          </div>
        )}
        <button
          onClick={load}
          className="text-xs text-zinc-500 hover:text-zinc-300"
        >
          Refresh
        </button>
      </div>
    </div>
  );
}
