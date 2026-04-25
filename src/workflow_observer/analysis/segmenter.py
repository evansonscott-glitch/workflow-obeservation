"""Send a window of raw events to Claude and get back named workflows.

The model receives a compact human-readable timeline (not raw JSON) so the
prompt is dense and tokens are spent on signal, not bookkeeping.
"""
import json
import os
import time
from typing import Optional

from ..storage import connect, load_settings

MODEL = "claude-sonnet-4-6"
MAX_OCR_SNIPPET = 200
MAX_EVENTS = 4000

SYSTEM_PROMPT = """You analyze a timeline of computer-activity events and group them into discrete workflows the user was performing.

For each workflow you identify, return a JSON object with these fields:
- name: short imperative phrase (e.g. "Triage support emails", "Process new order")
- description: 1-2 sentences describing what was being accomplished
- start_ts: Unix timestamp when the workflow started
- end_ts: Unix timestamp when the workflow ended
- systems_touched: list of apps/sites involved
- judgment_level: "low" (mechanical), "medium" (some interpretation), "high" (intuition-heavy)
- automation_potential: "high" (great agent candidate), "medium", or "low"
- notes: observations relevant to building an agent for this workflow

Output strict JSON in the form {"workflows": [...]}. Do not include any preamble, explanation, or markdown fences. Output JSON only."""


def _format_event(ts: float, source: str, kind: str, payload: dict) -> str:
    t = time.strftime("%H:%M:%S", time.localtime(ts))
    if source == "window":
        app = payload.get("app") or "?"
        title = payload.get("title") or "(no title)"
        return f"[{t}] focus: {app} — {title}"
    if source == "browser":
        url = payload.get("url") or ""
        title = payload.get("title") or ""
        return f"[{t}] browser/{kind}: {url} — {title}"
    if source == "ocr":
        app = payload.get("app") or "?"
        text = (payload.get("text") or "").replace("\n", " ")[:MAX_OCR_SNIPPET]
        return f"[{t}] ocr ({app}): {text}"
    return f"[{t}] {source}/{kind}: {json.dumps(payload)[:200]}"


def _resolve_api_key(api_key: Optional[str]) -> str:
    key = api_key or load_settings().get("claude_api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Claude API key not configured. Set it during onboarding or via ANTHROPIC_API_KEY.")
    return key


def _strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    text = text.lstrip("`")
    if "\n" in text:
        text = text.split("\n", 1)[1]
    return text.rsplit("```", 1)[0].strip()


def segment_window(start_ts: float, end_ts: float, api_key: Optional[str] = None) -> dict:
    key = _resolve_api_key(api_key)

    with connect() as c:
        rows = c.execute(
            "SELECT ts, source, kind, payload FROM events WHERE ts BETWEEN ? AND ? ORDER BY ts LIMIT ?",
            (start_ts, end_ts, MAX_EVENTS),
        ).fetchall()

    if not rows:
        return {"workflows": [], "event_count": 0, "saved_ids": []}

    timeline = "\n".join(
        _format_event(r["ts"], r["source"], r["kind"], json.loads(r["payload"])) for r in rows
    )

    from anthropic import Anthropic

    client = Anthropic(api_key=key)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Activity timeline:\n\n{timeline}"}],
    )

    raw = "".join(getattr(b, "text", "") for b in msg.content)
    stripped = _strip_fences(raw)
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude did not return valid JSON: {e}\n--- raw ---\n{raw[:1000]}")

    workflows = parsed.get("workflows", [])
    saved_ids: list[int] = []
    now = time.time()
    with connect() as c:
        for w in workflows:
            cur = c.execute(
                "INSERT INTO workflows (created, name, description, start_ts, end_ts, raw) VALUES (?,?,?,?,?,?)",
                (
                    now,
                    str(w.get("name") or "Unnamed"),
                    w.get("description"),
                    w.get("start_ts"),
                    w.get("end_ts"),
                    json.dumps(w),
                ),
            )
            saved_ids.append(int(cur.lastrowid))

    return {"workflows": workflows, "event_count": len(rows), "saved_ids": saved_ids}


def list_workflows(limit: int = 50) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT id, created, name, description, start_ts, end_ts, flagged_for_agent, raw "
            "FROM workflows ORDER BY created DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        if d.get("raw"):
            try:
                d["raw"] = json.loads(d["raw"])
            except json.JSONDecodeError:
                pass
        d["flagged_for_agent"] = bool(d["flagged_for_agent"])
        out.append(d)
    return out


def set_flag(workflow_id: int, flagged: bool) -> None:
    with connect() as c:
        c.execute(
            "UPDATE workflows SET flagged_for_agent = ? WHERE id = ?",
            (1 if flagged else 0, workflow_id),
        )
