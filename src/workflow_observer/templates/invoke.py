#!/usr/bin/env python3
"""Generic invoker for agents in this folder.

Usage:
    python scripts/invoke.py <agent-name> < input.txt
    echo "trigger payload" | python scripts/invoke.py <agent-name>
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / ".claude" / "agents"
LOG = ROOT / "shadow.log"

MODEL_ALIASES = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}


def load_agent(name):
    path = AGENTS / (name + ".md")
    if not path.exists():
        sys.exit("Agent file not found: " + str(path))
    text = path.read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if not m:
        sys.exit("Agent file has no frontmatter")
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm, m.group(2).strip()


def main():
    try:
        from anthropic import Anthropic
    except ImportError:
        sys.exit("Install: pip install anthropic")

    if len(sys.argv) < 2:
        sys.exit("Usage: invoke.py <agent-name> [trigger words]")
    name = sys.argv[1]
    fm, system_prompt = load_agent(name)
    if not sys.stdin.isatty():
        user_input = sys.stdin.read().strip()
    else:
        user_input = " ".join(sys.argv[2:]).strip()
    if not user_input:
        sys.exit("Pipe input or pass trigger as args")

    model = MODEL_ALIASES.get(fm.get("model", "sonnet"), fm.get("model", "claude-sonnet-4-6"))
    client = Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_input}],
    )
    text = "".join(getattr(b, "text", "") for b in msg.content)
    print(text)
    user = os.environ.get("USER", "?")
    with LOG.open("a") as f:
        f.write("\n--- " + name + " @ " + user + " ---\n" + text + "\n")


if __name__ == "__main__":
    main()
