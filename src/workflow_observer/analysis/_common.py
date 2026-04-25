import os
from typing import Optional

from ..storage import load_settings


def resolve_api_key(api_key: Optional[str] = None) -> str:
    key = api_key or load_settings().get("claude_api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "Claude API key not configured. Set it during onboarding or via ANTHROPIC_API_KEY."
        )
    return key


def strip_fences(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    text = text.lstrip("`")
    if "\n" in text:
        text = text.split("\n", 1)[1]
    return text.rsplit("```", 1)[0].strip()
