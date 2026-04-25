import { useEffect, useState } from "react";
import { api, RecentEvent, Status, Workflow } from "./api";
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
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [hoursBack, setHoursBack] = useState(4);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState("");

  const refresh = async () => {
    try {
      setWorkflows(await api.listWorkflows());
    } catch {}
  };

  useEffect(() => {
    refresh();
  }, []);

  const segment = async () => {
    setRunning(true);
    setErr("");
    try {
      await api.segment(hoursBack);
      await refresh();
    } catch (e) {
      setErr(String(e));
    } finally {
      setRunning(false);
    }
  };

  const toggleFlag = async (w: Workflow) => {
    await api.flagWorkflow(w.id, !w.flagged_for_agent);
    refresh();
  };

  return (
    <div>
      <div className="step-card" style={{ marginBottom: 16 }}>
        <h2>Segment recent activity</h2>
        <p>
          Send the last <strong>{hoursBack}</strong> hours of events to Claude
          and group them into named workflows.
        </p>
        <div className="row">
          <input
            type="number"
            min={0.5}
            step={0.5}
            value={hoursBack}
            onChange={(e) => setHoursBack(Number(e.target.value))}
            style={{ width: 80 }}
          />
          <button onClick={segment} disabled={running}>
            {running ? "Segmenting…" : "Segment now"}
          </button>
          {status?.observing ? (
            <span className="check">● observing</span>
          ) : (
            <span className="warn">● paused</span>
          )}
        </div>
        {err && <p className="err">{err}</p>}
      </div>

      <div className="step-card">
        <h2>Workflows</h2>
        {workflows.length === 0 ? (
          <p style={{ color: "#8a92a6" }}>No workflows yet. Run a segmentation pass.</p>
        ) : (
          workflows.map((w) => (
            <WorkflowRow key={w.id} w={w} onToggle={() => toggleFlag(w)} />
          ))
        )}
      </div>
    </div>
  );
}

function WorkflowRow({ w, onToggle }: { w: Workflow; onToggle: () => void }) {
  const r = w.raw;
  return (
    <div
      style={{
        padding: "12px 0",
        borderBottom: "1px dashed #232634",
      }}
    >
      <div className="row" style={{ justifyContent: "space-between" }}>
        <strong>{w.name}</strong>
        <button
          className="secondary"
          onClick={onToggle}
          style={{ padding: "4px 10px", fontSize: 12 }}
        >
          {w.flagged_for_agent ? "★ Flagged" : "☆ Flag for agent"}
        </button>
      </div>
      {w.description && <p style={{ margin: "6px 0", color: "#b8bdc9" }}>{w.description}</p>}
      <div style={{ fontSize: 12, color: "#8a92a6" }}>
        {r?.systems_touched?.join(", ") || "—"}
        {r?.judgment_level && <> · judgment: {r.judgment_level}</>}
        {r?.automation_potential && <> · automation: {r.automation_potential}</>}
      </div>
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
