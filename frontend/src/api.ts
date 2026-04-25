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
  completeOnboarding: () =>
    json<{ ok: boolean }>("/api/onboarding/complete", { method: "POST" }),
};
