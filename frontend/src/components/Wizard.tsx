import { useEffect, useState } from "react";
import { api, GmailConnectStatus, Status } from "../api";

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
      {step === 4 && <Gmail onNext={() => setStep(5)} />}
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

function Gmail({ onNext }: { onNext: () => void }) {
  const [credsText, setCredsText] = useState("");
  const [status, setStatus] = useState<GmailConnectStatus | null>(null);
  const [subjects, setSubjects] = useState<string[] | null>(null);
  const [uploadErr, setUploadErr] = useState("");

  useEffect(() => {
    let active = true;
    const tick = async () => {
      try {
        const s = await api.gmailConnectStatus();
        if (active) setStatus(s);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 1500);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  const upload = async () => {
    setUploadErr("");
    try {
      await api.uploadGmailCredentials(credsText);
      setCredsText("");
    } catch (e) {
      setUploadErr(String(e));
    }
  };

  const connect = async () => {
    setSubjects(null);
    await api.startGmailConnect();
  };

  const verify = async () => {
    const r = await api.gmailSample();
    setSubjects(r.subjects);
  };

  const hasCreds = status?.has_credentials;
  const connected = status?.connected;
  const running = status?.running;

  return (
    <StepCard
      title="Connect Gmail"
      body={
        <>
          <p>
            You'll need a Google Cloud OAuth client (Desktop app type) with the
            Gmail API enabled. Paste the contents of <code>credentials.json</code> here.
          </p>
          <ol style={{ fontSize: 13, color: "#8a92a6", lineHeight: 1.6 }}>
            <li>Go to console.cloud.google.com → APIs & Services → Credentials</li>
            <li>Create OAuth client ID → Application type: <strong>Desktop app</strong></li>
            <li>Enable the Gmail API (APIs & Services → Library)</li>
            <li>Add your email as a test user (OAuth consent screen)</li>
            <li>Download the JSON and paste it below</li>
          </ol>

          {!hasCreds ? (
            <>
              <textarea
                rows={4}
                placeholder='{"installed": {"client_id": "...", ...}}'
                value={credsText}
                onChange={(e) => setCredsText(e.target.value)}
                style={{
                  width: "100%",
                  fontFamily: "ui-monospace, monospace",
                  fontSize: 12,
                  background: "#0f1115",
                  color: "#e6e8eb",
                  border: "1px solid #232634",
                  borderRadius: 6,
                  padding: 8,
                  marginTop: 8,
                }}
              />
              {uploadErr && <p className="err">{uploadErr}</p>}
              <button
                onClick={upload}
                disabled={!credsText.trim()}
                style={{ marginTop: 8 }}
              >
                Save credentials
              </button>
            </>
          ) : connected ? (
            <p className="check">✔ Connected as {status?.email || "(unknown)"}</p>
          ) : running ? (
            <p className="warn">
              Browser window opened — grant access in Google to continue…
            </p>
          ) : status?.error ? (
            <p className="err">✘ {status.error}</p>
          ) : (
            <p>Credentials saved. Click <strong>Connect Gmail</strong>.</p>
          )}

          {subjects && (
            <ul>
              {subjects.length === 0 && <li>(no messages found)</li>}
              {subjects.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          )}
        </>
      }
      primary={
        connected
          ? { label: "Next", onClick: onNext }
          : hasCreds
            ? { label: running ? "Waiting…" : "Connect Gmail", onClick: connect, disabled: running }
            : { label: "Next", onClick: onNext, disabled: true }
      }
      secondary={connected ? { label: "Verify", onClick: verify } : undefined}
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
