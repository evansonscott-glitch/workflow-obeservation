export type Status = {
  version: string;
  platform: string;
  onboarded: boolean;
  claude_api_key_set: boolean;
  gmail_connected: boolean;
  observing: boolean;
};

export type RecentEvent = {
  ts: number;
  source: string;
  kind: string;
  payload: Record<string, unknown>;
};

const base = "";

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(base + path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  status: () => json<Status>("/api/status"),
  recentEvents: () => json<RecentEvent[]>("/api/events/recent?limit=30"),
  setClaudeKey: (key: string) =>
    json<{ ok: boolean }>("/api/onboarding/claude-key", {
      method: "POST",
      body: JSON.stringify({ api_key: key }),
    }),
  gmailSample: () =>
    json<{ connected: boolean; subjects: string[] }>("/api/gmail/sample"),
  uploadGmailCredentials: (content: string) =>
    json<{ ok: boolean }>("/api/gmail/credentials", {
      method: "POST",
      body: JSON.stringify({ content }),
    }),
  startGmailConnect: () =>
    json<{ ok: boolean }>("/api/gmail/connect", { method: "POST" }),
  gmailConnectStatus: () =>
    json<GmailConnectStatus>("/api/gmail/connect/status"),
  gmailDisconnect: () =>
    json<{ ok: boolean }>("/api/gmail/disconnect", { method: "POST" }),
  completeOnboarding: () =>
    json<{ ok: boolean }>("/api/onboarding/complete", { method: "POST" }),
  segment: (hoursBack: number) =>
    json<{ workflows: WorkflowSpec[]; event_count: number; saved_ids: number[] }>(
      "/api/segment",
      { method: "POST", body: JSON.stringify({ hours_back: hoursBack }) }
    ),
  listWorkflows: () => json<Workflow[]>("/api/workflows"),
  flagWorkflow: (id: number, flagged: boolean) =>
    json<{ ok: boolean }>(`/api/workflows/${id}/flag`, {
      method: "POST",
      body: JSON.stringify({ flagged }),
    }),
};

export type WorkflowSpec = {
  name: string;
  description?: string;
  start_ts?: number;
  end_ts?: number;
  systems_touched?: string[];
  judgment_level?: "low" | "medium" | "high";
  automation_potential?: "low" | "medium" | "high";
  notes?: string;
};

export type Workflow = {
  id: number;
  created: number;
  name: string;
  description: string | null;
  start_ts: number | null;
  end_ts: number | null;
  flagged_for_agent: boolean;
  raw: WorkflowSpec | null;
};

export type GmailConnectStatus = {
  connected: boolean;
  has_credentials: boolean;
  running: boolean;
  error: string | null;
  email: string | null;
};
