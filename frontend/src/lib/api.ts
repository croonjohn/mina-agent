const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
    opportunities: { post_title: string; platform: string; source: string; opportunity_type: string; suggested_angle: string }[];
    sentiment_summary: string;
    analyzed_at: string;
  }>("/api/v1/trends/");

// Publish
export const publishContent = (content_id: number) =>
  fetchAPI("/api/v1/publish/", { method: "POST", body: JSON.stringify({ content_id }) });

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
