import { useState } from "react";
import { api, Status } from "../api";

type Props = { status: Status; onUpdate: (s: Status) => void };

const STEPS = [
  "Welcome",
  "Permissions",
  "Claude API key",
  "Browser extension",
  "Gmail",
  "Test capture",
] as const;

export default function Wizard({ status, onUpdate }: Props) {
  const [step, setStep] = useState(0);
  return (
    <>
      <div className="steps">
        {STEPS.map((label, i) => (
          <span
            key={label}
            className={
              "step-pill " + (i === step ? "active" : i < step ? "done" : "")
            }
          >
            {i + 1}. {label}
          </span>
        ))}
      </div>
      {step === 0 && <Welcome onNext={() => setStep(1)} />}
      {step === 1 && <Permissions onNext={() => setStep(2)} />}
      {step === 2 && (
        <ClaudeKey
          done={status.claude_api_key_set}
          onNext={() => setStep(3)}
        />
      )}
      {step === 3 && <Extension onNext={() => setStep(4)} />}
      {step === 4 && (
        <Gmail
          connected={status.gmail_connected}
          onNext={() => setStep(5)}
        />
      )}
      {step === 5 && (
        <TestCapture
          onFinish={async () => {
            await api.completeOnboarding();
            const s = await api.status();
            onUpdate(s);
          }}
        />
      )}
    </>
  );
}

function StepCard({
  title,
  body,
  primary,
  secondary,
}: {
  title: string;
  body: React.ReactNode;
  primary: { label: string; onClick: () => void; disabled?: boolean };
  secondary?: { label: string; onClick: () => void };
}) {
  return (
    <div className="step-card">
      <h2>{title}</h2>
      {body}
      <div className="row" style={{ marginTop: 16 }}>
        <button onClick={primary.onClick} disabled={primary.disabled}>
          {primary.label}
        </button>
        {secondary && (
          <button className="secondary" onClick={secondary.onClick}>
            {secondary.label}
          </button>
        )}
      </div>
    </div>
  );
}

function Welcome({ onNext }: { onNext: () => void }) {
  return (
    <StepCard
      title="Welcome"
      body={
        <>
          <p>
            This tool watches how you work, segments your activity into named
            workflows, and helps you build Claude Code agents that handle the
            repetitive parts.
          </p>
          <p>
            All raw data stays on this Mac. Only segmented summaries you
            approve are sent to the Claude API.
          </p>
        </>
      }
      primary={{ label: "Get started", onClick: onNext }}
    />
  );
}

function Permissions({ onNext }: { onNext: () => void }) {
  return (
    <StepCard
      title="Grant macOS permissions"
      body={
        <>
          <p>
            Open <strong>System Settings → Privacy & Security</strong> and grant:
          </p>
          <ul>
            <li>Accessibility (window titles)</li>
            <li>Screen Recording (OCR of active window)</li>
            <li>Automation (control browser tabs)</li>
          </ul>
          <p className="warn">
            On Linux/dev: skip — these are macOS-only and the daemon will no-op.
          </p>
        </>
      }
      primary={{ label: "Continue", onClick: onNext }}
    />
  );
}

function ClaudeKey({ done, onNext }: { done: boolean; onNext: () => void }) {
  const [key, setKey] = useState("");
  const [state, setState] = useState<"idle" | "testing" | "ok" | "err">(
    done ? "ok" : "idle"
  );
  const [err, setErr] = useState("");
  const submit = async () => {
    setState("testing");
    setErr("");
    try {
      await api.setClaudeKey(key);
      setState("ok");
    } catch (e) {
      setErr(String(e));
      setState("err");
    }
  };
  return (
    <StepCard
      title="Claude API key"
      body={
        <>
          <p>Paste your Anthropic API key. We'll do a tiny test call to confirm it works.</p>
          <input
            type="password"
            placeholder="sk-ant-…"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            disabled={state === "testing"}
          />
          {state === "testing" && <p>Testing…</p>}
          {state === "ok" && <p className="check">✔ API key works.</p>}
          {state === "err" && <p className="err">✘ {err}</p>}
        </>
      }
      primary={
        state === "ok"
          ? { label: "Next", onClick: onNext }
          : { label: "Test & save", onClick: submit, disabled: !key }
      }
    />
  );
}

function Extension({ onNext }: { onNext: () => void }) {
  return (
    <StepCard
      title="Install Chrome extension"
      body={
        <>
          <p>
            Load the unpacked extension from the <code>extension/</code> folder
            in this repo:
          </p>
          <ol>
            <li>Open <code>chrome://extensions</code></li>
            <li>Toggle <strong>Developer mode</strong> on (top right)</li>
            <li>Click <strong>Load unpacked</strong> and pick the <code>extension/</code> folder</li>
          </ol>
          <p>The extension will connect to <code>ws://127.0.0.1:8765/ws/browser</code>.</p>
        </>
      }
      primary={{ label: "Continue", onClick: onNext }}
    />
  );
}

function Gmail({ connected, onNext }: { connected: boolean; onNext: () => void }) {
  const [subjects, setSubjects] = useState<string[] | null>(null);
  const verify = async () => {
    const r = await api.gmailSample();
    setSubjects(r.subjects);
  };
  return (
    <StepCard
      title="Connect Gmail"
      body={
        <>
          <p>
            Run the OAuth flow (TODO: wire `/api/gmail/connect`). Once
            connected, click verify to see your last few subjects.
          </p>
          {connected ? (
            <p className="check">✔ Gmail connected.</p>
          ) : (
            <p className="warn">Not connected yet.</p>
          )}
          {subjects && (
            <ul>
              {subjects.length === 0 && <li>(no messages or not connected)</li>}
              {subjects.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          )}
        </>
      }
      primary={{ label: "Next", onClick: onNext }}
      secondary={{ label: "Verify", onClick: verify }}
    />
  );
}

function TestCapture({ onFinish }: { onFinish: () => void }) {
  return (
    <StepCard
      title="Test capture"
      body={
        <>
          <p>
            Switch between a few apps and tabs for ~30 seconds. Watch the
            activity panel on the right — you should see new events appear.
          </p>
          <p>Once you see events, you're done with setup.</p>
        </>
      }
      primary={{ label: "Finish setup", onClick: onFinish }}
    />
  );
}
