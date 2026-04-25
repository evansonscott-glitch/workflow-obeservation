"""Turn saved agents into a Claude Code-ready folder.

Output layout:
    export-<ts>/
      .claude/agents/<name>.md       # subagent file with frontmatter
      .mcp.json                      # combined MCP server stubs
      RUNBOOK.md                     # human-readable runbook
      scripts/invoke.py              # generic single-agent invoker
"""
import io
import json
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .analysis import agent_designer
from .config import app_support_dir

SHADOW_PREAMBLE = """[MODE: SHADOW]
You are operating in shadow mode. Do not take any side-effecting actions
(no sending, no writing, no deleting, no external calls that change state).
For each action you would take, describe it in detail and stop. The user
reviews your output and decides whether to execute.

---

"""

SUPERVISED_PREAMBLE = """[MODE: SUPERVISED]
For every side-effecting action (sending, writing, deleting, calling external
services that change state), describe the action and ask the user to confirm
before proceeding. Read-only actions can run freely.

---

"""

_INVOKE_TEMPLATE = Path(__file__).resolve().parent / "templates" / "invoke.py"


def render_agent_md(spec: dict, mode: str) -> str:
    name = spec.get("name") or "unnamed-agent"
    frontmatter_lines = [f"name: {name}"]
    if spec.get("description"):
        desc = str(spec["description"]).replace("\n", " ").strip()
        frontmatter_lines.append(f"description: {desc}")
    if spec.get("model"):
        frontmatter_lines.append(f"model: {spec['model']}")
    if spec.get("tools"):
        frontmatter_lines.append(f"tools: {', '.join(spec['tools'])}")

    frontmatter = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n"

    preamble = ""
    if mode == "shadow":
        preamble = SHADOW_PREAMBLE
    elif mode == "supervised":
        preamble = SUPERVISED_PREAMBLE

    body = (spec.get("system_prompt") or "").rstrip() + "\n"
    return frontmatter + preamble + body


def render_mcp_json(agents: list[dict]) -> str:
    servers: dict[str, dict] = {}
    for a in agents:
        for m in a["spec"].get("mcp_servers") or []:
            sname = m.get("name")
            if not sname or sname in servers:
                continue
            servers[sname] = {
                "command": "TODO_REPLACE_WITH_MCP_SERVER_COMMAND",
                "args": [],
                "env": {},
                "_purpose": m.get("purpose", ""),
            }
    return json.dumps({"mcpServers": servers}, indent=2) + "\n"


def render_runbook(agents: list[dict]) -> str:
    parts: list[str] = [
        "# Workflow Observer — Generated Agents",
        "",
        f"Generated {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Drop this folder into the root of your Claude Code project. Edit "
        "`.mcp.json` to wire up the actual MCP server commands listed below.",
        "",
    ]
    for a in agents:
        spec = a["spec"]
        mode = a["mode"]
        title = spec.get("display_name") or spec.get("name", "Unnamed")
        parts += [
            f"## {title} (`{spec.get('name','unnamed')}`)",
            "",
            f"- **Mode:** {mode}",
            f"- **Trigger:** {spec.get('trigger', 'on demand')}",
            f"- **Model:** {spec.get('model', 'sonnet')}",
        ]
        if spec.get("tools"):
            parts.append(f"- **Tools:** {', '.join(spec['tools'])}")
        if spec.get("description"):
            parts += ["", spec["description"]]

        if spec.get("improvements"):
            parts += ["", "### Improvements over the human workflow", ""]
            for imp in spec["improvements"]:
                parts += [
                    f"- **Observed:** {imp.get('observed','')}",
                    f"  - **Agent approach:** {imp.get('agent_approach','')}",
                    f"  - **Why better:** {imp.get('why_better','')}",
                ]

        if spec.get("escalation"):
            parts += ["", "### Escalation rules", ""]
            for e in spec["escalation"]:
                parts.append(f"- {e}")

        if spec.get("mcp_servers"):
            parts += ["", "### Required MCP servers", ""]
            for m in spec["mcp_servers"]:
                parts.append(f"- **{m.get('name','?')}** — {m.get('purpose','')}")

        parts += [
            "",
            "### Trust ladder",
            "",
            "1. **shadow** (current default): agent describes actions, takes none.",
            "2. **supervised**: agent confirms each side-effecting action.",
            "3. **autonomous**: agent acts and logs a daily summary.",
            "",
            "Promote by re-exporting from Workflow Observer with the new mode.",
            "",
            "---",
            "",
        ]
    return "\n".join(parts)


def _files_for(agents: list[dict]) -> dict[str, str]:
    files: dict[str, str] = {}
    invoke_script = _INVOKE_TEMPLATE.read_text()
    for a in agents:
        name = a["spec"].get("name") or f"agent-{a['id']}"
        files[f".claude/agents/{name}.md"] = render_agent_md(a["spec"], a["mode"])
    files[".mcp.json"] = render_mcp_json(agents)
    files["RUNBOOK.md"] = render_runbook(agents)
    files["scripts/invoke.py"] = invoke_script
    return files


def package_to_dir(dest: Path, agent_ids: Optional[list[int]] = None) -> dict:
    agents = _select_agents(agent_ids)
    if not agents:
        raise RuntimeError("No agents to export.")
    dest.mkdir(parents=True, exist_ok=True)
    files = _files_for(agents)
    for rel, content in files.items():
        path = dest / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return {"path": str(dest), "agents": [a["name"] for a in agents], "files": list(files)}


def package_to_zip(agent_ids: Optional[list[int]] = None) -> bytes:
    agents = _select_agents(agent_ids)
    if not agents:
        raise RuntimeError("No agents to export.")
    files = _files_for(agents)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, content in files.items():
            z.writestr(rel, content)
    return buf.getvalue()


def default_export_dir() -> Path:
    return app_support_dir() / "exports" / f"export-{int(time.time())}"


def _select_agents(agent_ids: Optional[list[int]]) -> list[dict]:
    all_agents = agent_designer.list_agents()
    if agent_ids is None:
        return all_agents
    wanted = set(agent_ids)
    return [a for a in all_agents if a["id"] in wanted]
