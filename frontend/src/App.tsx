import { useEffect, useState } from "react";
import { api, RecentEvent, Status } from "./api";
import Wizard from "./components/Wizard";

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [events, setEvents] = useState<RecentEvent[]>([]);

  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        const [s, e] = await Promise.all([api.status(), api.recentEvents()]);
        if (active) {
          setStatus(s);
          setEvents(e);
        }
      } catch {
        // backend may not be up yet during dev
      }
    };
    tick();
    const id = setInterval(tick, 2000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="layout">
      <div className="main">
        <h1>Workflow Observer</h1>
        <div className="step-meta">
          {status ? (
            <>v{status.version} · {status.platform} · {status.onboarded ? "onboarded" : "setup mode"}</>
          ) : (
            "connecting to local server…"
          )}
        </div>
        {status && !status.onboarded ? (
          <Wizard status={status} onUpdate={setStatus} />
        ) : (
          <Dashboard status={status} />
        )}
      </div>
      <ActivityPanel events={events} />
    </div>
  );
}

function Dashboard({ status }: { status: Status | null }) {
  return (
    <div className="step-card">
      <h2>Dashboard</h2>
      <p>You're set up. Tabs for Live / Today / Workflows / Agents / Export will live here.</p>
      {status?.observing ? (
        <p className="check">● Observing</p>
      ) : (
        <p className="warn">● Paused</p>
      )}
    </div>
  );
}

function ActivityPanel({ events }: { events: RecentEvent[] }) {
  return (
    <aside className="activity">
      <h3>Live activity</h3>
      {events.length === 0 ? (
        <div className="event">No events yet.</div>
      ) : (
        events.map((e, i) => (
          <div className="event" key={i}>
            <span className="src">{e.source}/{e.kind}</span>
            {summarize(e.payload)}
          </div>
        ))
      )}
    </aside>
  );
}

function summarize(p: Record<string, unknown>): string {
  const candidates = ["title", "url", "app", "subject"];
  for (const k of candidates) {
    if (typeof p[k] === "string") return p[k] as string;
  }
  return JSON.stringify(p).slice(0, 80);
}
