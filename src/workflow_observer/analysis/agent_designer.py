"""Take a flagged workflow and ask Claude to design an agent that does it
better than the human currently does — automating sub-steps, batching,
adding safety checks, catching edge cases.
"""
import json
import time
from typing import Optional

from ..storage import connect
from ._common import resolve_api_key, strip_fences

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You design Claude Code agents that automate a workflow described to you.

The user is showing you a workflow they currently do manually. Your job is to design an agent that:
1. Reproduces what they do (so they trust it).
2. Improves on it where possible — automating sub-steps, batching, adding safety checks, catching edge cases the human currently misses.

Return strict JSON with these fields:
- name: kebab-case slug (e.g. "triage-support-emails")
- display_name: human-readable name
- description: when to invoke (1-2 sentences in the style of a Claude Code subagent description)
- model: "haiku" | "sonnet" | "opus" — pick the cheapest model that can do the job well
- system_prompt: the full system prompt for the agent (be concrete, opinionated, include the actual rules)
- tools: array of tool/MCP names the agent needs (e.g. ["gmail_read", "gmail_draft", "Read", "Write", "Bash"])
- mcp_servers: array of {name, purpose} for any MCP servers needed (gmail, shopify, etc.)
- trigger: when this agent should run (e.g. "on demand", "every weekday at 9am", "when an email matching X arrives")
- improvements: array of {observed: string, agent_approach: string, why_better: string} — concrete improvements over what the human does
- escalation: array of conditions where the agent should pause and ask the human
- default_mode: almost always "shadow" — start safe

Output JSON only. No preamble, no markdown fences."""


def design_agent(workflow_id: int, api_key: Optional[str] = None) -> dict:
    key = resolve_api_key(api_key)

    with connect() as c:
        row = c.execute(
            "SELECT id, name, description, start_ts, end_ts, raw FROM workflows WHERE id = ?",
            (workflow_id,),
        ).fetchone()
    if not row:
        raise RuntimeError(f"Workflow {workflow_id} not found")

    workflow: dict = {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "start_ts": row["start_ts"],
        "end_ts": row["end_ts"],
    }
    if row["raw"]:
        try:
            workflow.update(json.loads(row["raw"]))
        except json.JSONDecodeError:
            pass

    from anthropic import Anthropic

    client = Anthropic(api_key=key)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": f"Workflow:\n\n{json.dumps(workflow, indent=2, default=str)}"}
        ],
    )
    raw = "".join(getattr(b, "text", "") for b in msg.content)
    try:
        spec = json.loads(strip_fences(raw))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Claude did not return valid JSON: {e}\n--- raw ---\n{raw[:1000]}")

    spec.setdefault("default_mode", "shadow")
    spec["source_workflow_id"] = workflow_id
    return spec


def save_agent(spec: dict) -> int:
    name = str(spec.get("name") or "unnamed-agent")
    mode = str(spec.get("default_mode") or "shadow")
    with connect() as c:
        cur = c.execute(
            "INSERT INTO agents (created, name, mode, spec) VALUES (?,?,?,?)",
            (time.time(), name, mode, json.dumps(spec)),
        )
        return int(cur.lastrowid)


def list_agents() -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT id, created, name, mode, spec FROM agents ORDER BY created DESC"
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        d = dict(r)
        try:
            d["spec"] = json.loads(d["spec"])
        except json.JSONDecodeError:
            pass
        out.append(d)
    return out


def get_agent(agent_id: int) -> Optional[dict]:
    with connect() as c:
        row = c.execute(
            "SELECT id, created, name, mode, spec FROM agents WHERE id = ?", (agent_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["spec"] = json.loads(d["spec"])
    except json.JSONDecodeError:
        pass
    return d


def update_agent(agent_id: int, spec: dict) -> None:
    name = str(spec.get("name") or "unnamed-agent")
    with connect() as c:
        c.execute(
            "UPDATE agents SET name = ?, spec = ? WHERE id = ?",
            (name, json.dumps(spec), agent_id),
        )


def set_mode(agent_id: int, mode: str) -> None:
    if mode not in ("shadow", "supervised", "autonomous"):
        raise ValueError(f"Invalid mode: {mode}")
    with connect() as c:
        c.execute("UPDATE agents SET mode = ? WHERE id = ?", (mode, agent_id))


def delete_agent(agent_id: int) -> None:
    with connect() as c:
        c.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
