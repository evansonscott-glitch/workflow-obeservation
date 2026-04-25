import { useEffect, useState } from "react";
import { Agent, AgentMode, api } from "../api";
import AgentEditor from "./AgentEditor";

export default function AgentList() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [editing, setEditing] = useState<number | null>(null);

  const refresh = async () => {
    try {
      setAgents(await api.listAgents());
    } catch {}
  };

  useEffect(() => {
    refresh();
  }, []);

  const setMode = async (id: number, mode: AgentMode) => {
    await api.setAgentMode(id, mode);
    refresh();
  };

  const remove = async (id: number) => {
    if (!confirm("Delete this agent?")) return;
    await api.deleteAgent(id);
    refresh();
  };

  return (
    <div>
      {agents.length === 0 ? (
        <p style={{ color: "#8a92a6" }}>No saved agents yet.</p>
      ) : (
        agents.map((a) => (
          <div key={a.id} style={{ padding: "12px 0", borderBottom: "1px dashed #232634" }}>
            <div className="row" style={{ justifyContent: "space-between" }}>
              <strong>{a.spec.display_name || a.name}</strong>
              <div className="row">
                <select
                  value={a.mode}
                  onChange={(e) => setMode(a.id, e.target.value as AgentMode)}
                  style={{ fontSize: 12 }}
                >
                  <option value="shadow">shadow</option>
                  <option value="supervised">supervised</option>
                  <option value="autonomous">autonomous</option>
                </select>
                <button
                  className="secondary"
                  onClick={() => setEditing(editing === a.id ? null : a.id)}
                  style={{ padding: "4px 10px", fontSize: 12 }}
                >
                  {editing === a.id ? "Close" : "Edit"}
                </button>
                <button
                  className="secondary"
                  onClick={() => remove(a.id)}
                  style={{ padding: "4px 10px", fontSize: 12 }}
                >
                  Delete
                </button>
              </div>
            </div>
            {a.spec.description && (
              <p style={{ margin: "6px 0", color: "#b8bdc9" }}>{a.spec.description}</p>
            )}
            <div style={{ fontSize: 12, color: "#8a92a6" }}>
              {a.spec.model || "sonnet"} · {a.spec.trigger || "on demand"}
              {a.spec.tools?.length ? ` · tools: ${a.spec.tools.join(", ")}` : ""}
            </div>
            {editing === a.id && (
              <div style={{ marginTop: 12 }}>
                <AgentEditor
                  initial={a.spec}
                  saveLabel="Update agent"
                  onSave={async (spec) => {
                    await api.updateAgent(a.id, spec);
                    setEditing(null);
                    refresh();
                  }}
                  onCancel={() => setEditing(null)}
                />
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
