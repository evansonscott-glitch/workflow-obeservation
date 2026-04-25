import { useState } from "react";
import { AgentSpec } from "../api";

type Props = {
  initial: AgentSpec;
  onSave: (spec: AgentSpec) => void | Promise<void>;
  onCancel?: () => void;
  saveLabel?: string;
};

export default function AgentEditor({ initial, onSave, onCancel, saveLabel = "Save agent" }: Props) {
  const [spec, setSpec] = useState<AgentSpec>(initial);
  const [saving, setSaving] = useState(false);

  const set = <K extends keyof AgentSpec>(k: K, v: AgentSpec[K]) =>
    setSpec((s) => ({ ...s, [k]: v }));

  const setLines = (k: "tools" | "escalation", text: string) =>
    set(k, text.split("\n").map((l) => l.trim()).filter(Boolean));

  const linesValue = (arr?: string[]) => (arr || []).join("\n");

  const updateImprovement = (i: number, field: keyof NonNullable<AgentSpec["improvements"]>[number], v: string) => {
    const arr = [...(spec.improvements || [])];
    arr[i] = { ...arr[i], [field]: v };
    set("improvements", arr);
  };

  const addImprovement = () =>
    set("improvements", [...(spec.improvements || []), { observed: "", agent_approach: "", why_better: "" }]);
  const removeImprovement = (i: number) =>
    set("improvements", (spec.improvements || []).filter((_, j) => j !== i));

  const updateMcp = (i: number, field: "name" | "purpose", v: string) => {
    const arr = [...(spec.mcp_servers || [])];
    arr[i] = { ...arr[i], [field]: v };
    set("mcp_servers", arr);
  };
  const addMcp = () => set("mcp_servers", [...(spec.mcp_servers || []), { name: "", purpose: "" }]);
  const removeMcp = (i: number) => set("mcp_servers", (spec.mcp_servers || []).filter((_, j) => j !== i));

  const submit = async () => {
    setSaving(true);
    try {
      await onSave(spec);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ display: "grid", gap: 12 }}>
      <Field label="Name (slug)">
        <input type="text" value={spec.name || ""} onChange={(e) => set("name", e.target.value)} />
      </Field>
      <Field label="Display name">
        <input
          type="text"
          value={spec.display_name || ""}
          onChange={(e) => set("display_name", e.target.value)}
        />
      </Field>
      <Field label="Description (when to invoke)">
        <textarea
          rows={2}
          value={spec.description || ""}
          onChange={(e) => set("description", e.target.value)}
        />
      </Field>

      <div className="row" style={{ gap: 16 }}>
        <Field label="Model" style={{ flex: 1 }}>
          <select
            value={spec.model || "sonnet"}
            onChange={(e) => set("model", e.target.value as AgentSpec["model"])}
          >
            <option value="haiku">haiku</option>
            <option value="sonnet">sonnet</option>
            <option value="opus">opus</option>
          </select>
        </Field>
        <Field label="Default mode" style={{ flex: 1 }}>
          <select
            value={spec.default_mode || "shadow"}
            onChange={(e) => set("default_mode", e.target.value as AgentSpec["default_mode"])}
          >
            <option value="shadow">shadow</option>
            <option value="supervised">supervised</option>
            <option value="autonomous">autonomous</option>
          </select>
        </Field>
      </div>

      <Field label="Trigger">
        <input
          type="text"
          value={spec.trigger || ""}
          onChange={(e) => set("trigger", e.target.value)}
          placeholder="on demand / cron: 9am weekdays / when email matches X"
        />
      </Field>

      <Field label="System prompt">
        <textarea
          rows={10}
          value={spec.system_prompt || ""}
          onChange={(e) => set("system_prompt", e.target.value)}
        />
      </Field>

      <Field label="Tools (one per line)">
        <textarea
          rows={4}
          value={linesValue(spec.tools)}
          onChange={(e) => setLines("tools", e.target.value)}
        />
      </Field>

      <Field label="Escalation conditions (one per line)">
        <textarea
          rows={3}
          value={linesValue(spec.escalation)}
          onChange={(e) => setLines("escalation", e.target.value)}
        />
      </Field>

      <div>
        <div style={labelStyle}>MCP servers</div>
        {(spec.mcp_servers || []).map((m, i) => (
          <div key={i} className="row" style={{ marginBottom: 6 }}>
            <input
              style={{ flex: 1 }}
              placeholder="name"
              value={m.name}
              onChange={(e) => updateMcp(i, "name", e.target.value)}
            />
            <input
              style={{ flex: 2 }}
              placeholder="purpose"
              value={m.purpose}
              onChange={(e) => updateMcp(i, "purpose", e.target.value)}
            />
            <button className="secondary" onClick={() => removeMcp(i)}>×</button>
          </div>
        ))}
        <button className="secondary" onClick={addMcp}>+ Add MCP server</button>
      </div>

      <div>
        <div style={labelStyle}>Improvements over the human workflow</div>
        {(spec.improvements || []).map((imp, i) => (
          <div
            key={i}
            style={{ background: "#0f1115", padding: 8, borderRadius: 6, marginBottom: 8 }}
          >
            <input
              placeholder="What you observed"
              value={imp.observed}
              onChange={(e) => updateImprovement(i, "observed", e.target.value)}
              style={{ marginBottom: 4 }}
            />
            <input
              placeholder="How the agent will do it"
              value={imp.agent_approach}
              onChange={(e) => updateImprovement(i, "agent_approach", e.target.value)}
              style={{ marginBottom: 4 }}
            />
            <input
              placeholder="Why that's better"
              value={imp.why_better}
              onChange={(e) => updateImprovement(i, "why_better", e.target.value)}
            />
            <button
              className="secondary"
              onClick={() => removeImprovement(i)}
              style={{ marginTop: 4, fontSize: 12, padding: "2px 8px" }}
            >
              Remove
            </button>
          </div>
        ))}
        <button className="secondary" onClick={addImprovement}>+ Add improvement</button>
      </div>

      <div className="row" style={{ marginTop: 8 }}>
        <button onClick={submit} disabled={saving || !spec.name}>
          {saving ? "Saving…" : saveLabel}
        </button>
        {onCancel && (
          <button className="secondary" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  fontSize: 12,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "#8a92a6",
  marginBottom: 4,
};

function Field({
  label,
  children,
  style,
}: {
  label: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}) {
  return (
    <div style={style}>
      <div style={labelStyle}>{label}</div>
      {children}
    </div>
  );
}
