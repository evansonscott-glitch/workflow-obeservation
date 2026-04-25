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
  designAgent: (workflowId: number) =>
    json<AgentSpec>("/api/agents/design", {
      method: "POST",
      body: JSON.stringify({ workflow_id: workflowId }),
    }),
  saveAgent: (spec: AgentSpec) =>
    json<{ id: number }>("/api/agents", {
      method: "POST",
      body: JSON.stringify({ spec }),
    }),
  listAgents: () => json<Agent[]>("/api/agents"),
  updateAgent: (id: number, spec: AgentSpec) =>
    json<{ ok: boolean }>(`/api/agents/${id}`, {
      method: "PUT",
      body: JSON.stringify({ spec }),
    }),
  setAgentMode: (id: number, mode: AgentMode) =>
    json<{ ok: boolean }>(`/api/agents/${id}/mode`, {
      method: "POST",
      body: JSON.stringify({ mode }),
    }),
  deleteAgent: (id: number) =>
    json<{ ok: boolean }>(`/api/agents/${id}`, { method: "DELETE" }),
};

export type AgentMode = "shadow" | "supervised" | "autonomous";

export type AgentImprovement = {
  observed: string;
  agent_approach: string;
  why_better: string;
};

export type AgentSpec = {
  name: string;
  display_name?: string;
  description?: string;
  model?: "haiku" | "sonnet" | "opus";
  system_prompt?: string;
  tools?: string[];
  mcp_servers?: { name: string; purpose: string }[];
  trigger?: string;
  improvements?: AgentImprovement[];
  escalation?: string[];
  default_mode?: AgentMode;
  source_workflow_id?: number;
};

export type Agent = {
  id: number;
  created: number;
  name: string;
  mode: AgentMode;
  spec: AgentSpec;
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
