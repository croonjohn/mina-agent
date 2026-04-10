const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchAPI<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

// Pipeline
export const runPipeline = (body: {
  platforms?: string[];
  tiers?: number[];
  content_types?: string[];
  auto_approve?: boolean;
}) => fetchAPI<{ pipeline_id: string; status: string; message: string }>("/api/v1/pipeline/run", { method: "POST", body: JSON.stringify(body) });

export const getPipelineStatus = (id: string) =>
  fetchAPI<{
    pipeline_id: string;
    status: string;
    steps: Record<string, any>;
    posts_scraped: number;
    contents_generated: number;
    contents_published: number;
    started_at: string | null;
    completed_at: string | null;
    error: string | null;
  }>(`/api/v1/pipeline/status/${id}`);

export const getPipelineHistory = (limit = 20) =>
  fetchAPI<
    {
      pipeline_id: string;
      status: string;
      posts_scraped: number;
      contents_generated: number;
      started_at: string | null;
      completed_at: string | null;
    }[]
  >(`/api/v1/pipeline/history?limit=${limit}`);

// Content
export const getContentQueue = (status?: string, limit = 50) => {
  const params = new URLSearchParams({ limit: String(limit) });
  if (status) params.set("status", status);
  return fetchAPI<
    {
      id: number;
      platform: string;
      target: string;
      content_type: string;
      title: string | null;
      body: string;
      status: string;
      created_at: string;
      approved_at: string | null;
      published_at: string | null;
      source_post_url?: string;
    }[]
  >(`/api/v1/content/queue?${params}`);
};

export const getContentItem = (id: number) =>
  fetchAPI<{
    id: number;
    platform: string;
    target: string;
    content_type: string;
    title: string | null;
    body: string;
    status: string;
    trend_context: any;
    created_at: string;
  }>(`/api/v1/content/${id}`);

export const updateContent = (id: number, body: { title?: string; body?: string }) =>
  fetchAPI(`/api/v1/content/${id}`, { method: "PUT", body: JSON.stringify(body) });

export const approveContent = (id: number) =>
  fetchAPI(`/api/v1/content/${id}/approve`, { method: "POST" });

export const rejectContent = (id: number) =>
  fetchAPI(`/api/v1/content/${id}/reject`, { method: "POST" });

export const batchApprove = (ids: number[]) =>
  fetchAPI<{ approved: number }>("/api/v1/content/batch-approve", { method: "POST", body: JSON.stringify({ content_ids: ids }) });

export const batchReject = (ids: number[]) =>
  fetchAPI<{ rejected: number }>("/api/v1/content/batch-reject", { method: "POST", body: JSON.stringify({ content_ids: ids }) });

// Trends
export const getLatestTrends = () =>
  fetchAPI<{
    topics: { keyword: string; description: string; relevance_to_verse8: string; post_count: number }[];
    opportunities: { post_title: string; platform: string; source: string; opportunity_type: string; suggested_angle: string; post_url?: string }[];
    sentiment_summary: string;
    analyzed_at: string;
  }>("/api/v1/trends/");

// Publish (semi-automatic: copy + open link)
export const publishContent = (content_id: number) =>
  fetchAPI<{
    success: boolean;
    content_id: number;
    platform: string;
    method: string;
    target_url: string;
    title: string | null;
    body: string;
    content_type: string;
    instructions: string;
  }>("/api/v1/publish/", { method: "POST", body: JSON.stringify({ content_id }) });

export const markAsPublished = (content_id: number, external_url?: string) =>
  fetchAPI("/api/v1/publish/mark-published", {
    method: "POST",
    body: JSON.stringify({ content_id, external_url }),
  });

export const getPublishHistory = (limit = 50) =>
  fetchAPI<
    {
      id: number;
      content_id: number;
      platform: string;
      external_url: string | null;
      score: number;
      comment_count: number;
      published_at: string;
    }[]
  >(`/api/v1/publish/history?limit=${limit}`);

// Templates
export interface Template {
  id: string;
  name: string;
  platform: string;
  content_type: string;
  template_text: string;
  updated_at: string;
}

export const getTemplates = () =>
  fetchAPI<Template[]>("/api/v1/templates/");

export const getTemplate = (id: string) =>
  fetchAPI<Template>(`/api/v1/templates/${id}`);

export const createTemplate = (body: { name: string; platform: string; content_type: string; template_text: string }) =>
  fetchAPI<Template>("/api/v1/templates/", { method: "POST", body: JSON.stringify(body) });

export const updateTemplate = (id: string, body: { name?: string; platform?: string; content_type?: string; template_text?: string }) =>
  fetchAPI<Template>(`/api/v1/templates/${id}`, { method: "PUT", body: JSON.stringify(body) });

export const deleteTemplate = (id: string) =>
  fetchAPI(`/api/v1/templates/${id}`, { method: "DELETE" });

export const seedTemplates = () =>
  fetchAPI<{ message: string }>("/api/v1/templates/seed", { method: "POST" });

// Tone Guide / Guidelines
export interface ToneGuide {
  use_words: string[];
  avoid_words: string[];
  principles: string[];
}

export const getToneGuide = () =>
  fetchAPI<ToneGuide>("/api/v1/guidelines/tone");

export const updateToneGuide = (body: ToneGuide) =>
  fetchAPI<ToneGuide>("/api/v1/guidelines/tone", { method: "PUT", body: JSON.stringify(body) });

// Escalations
export interface Escalation {
  id: number;
  level: number;
  trigger_type: string;
  description: string;
  ai_draft_response: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

export const getEscalations = (status?: string, level?: number) => {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (level !== undefined) params.set("level", String(level));
  return fetchAPI<Escalation[]>(`/api/v1/escalations/?${params}`);
};

export const resolveEscalation = (id: number) =>
  fetchAPI(`/api/v1/escalations/${id}/resolve`, { method: "POST" });

export const dismissEscalation = (id: number) =>
  fetchAPI(`/api/v1/escalations/${id}/dismiss`, { method: "POST" });

export const getEscalationCount = () =>
  fetchAPI<{ open: number }>("/api/v1/escalations/count");

// Metrics
export interface MetricsSummary {
  period: string;
  since: string;
  pipelines: {
    total_runs: number;
    total_scraped: number;
    total_generated: number;
  };
  content: {
    by_status: {
      pending: number;
      approved: number;
      published: number;
      rejected: number;
      failed: number;
    };
    total: number;
  };
  published: {
    count: number;
    avg_score: number;
    avg_comments: number;
    total_score: number;
    total_comments: number;
  };
  escalations: {
    open: number;
    resolved: number;
    total: number;
  };
}

export const getMetrics = (period: string = "weekly") =>
  fetchAPI<MetricsSummary>(`/api/v1/metrics/summary?period=${period}`);

// Settings / Subreddits
export interface SubredditConfig {
  name: string;
  tier: number;
  enabled: boolean;
}

export const getSubreddits = () =>
  fetchAPI<SubredditConfig[]>("/api/v1/settings/subreddits");

export const addSubreddit = (body: { name: string; tier: number }) =>
  fetchAPI("/api/v1/settings/subreddits", { method: "POST", body: JSON.stringify(body) });

export const removeSubreddit = (name: string) =>
  fetchAPI(`/api/v1/settings/subreddits/${name}`, { method: "DELETE" });

export const getDiscordWebhook = () =>
  fetchAPI<{ url: string }>("/api/v1/settings/discord-webhook");

export const updateDiscordWebhook = (url: string) =>
  fetchAPI("/api/v1/settings/discord-webhook", { method: "PUT", body: JSON.stringify({ url }) });

export const testDiscordWebhook = () =>
  fetchAPI<{ success: boolean; message: string }>("/api/v1/settings/discord-webhook/test", { method: "POST" });

export const getHealthCheck = () =>
  fetchAPI<{ status: string; version: string; service: string; uptime: string; database: string }>("/api/v1/health");
