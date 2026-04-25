import asyncio
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .observers import browser as browser_obs
from .observers import gmail as gmail_obs
from .observers import window as window_obs
from .storage import init_db, load_settings, recent_events, save_settings


def find_frontend_dist() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        Path(__file__).resolve().parent.parent.parent.parent / "frontend_dist",
    ]
    for c in candidates:
        if c.exists() and (c / "index.html").exists():
            return c
    return None


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Workflow Observer", version=__version__)

    app.include_router(browser_obs.router)

    @app.get("/api/status")
    def status() -> dict:
        s = load_settings()
        return {
            "version": __version__,
            "platform": sys.platform,
            "onboarded": bool(s.get("onboarded")),
            "claude_api_key_set": bool(s.get("claude_api_key")),
            "gmail_connected": gmail_obs.is_connected(),
            "observing": s.get("observing", False),
        }

    @app.get("/api/events/recent")
    def events_recent(limit: int = 50) -> list[dict]:
        return recent_events(limit)

    class ClaudeKey(BaseModel):
        api_key: str

    @app.post("/api/onboarding/claude-key")
    async def set_claude_key(body: ClaudeKey) -> dict:
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise HTTPException(500, f"anthropic SDK missing: {e}")
        client = Anthropic(api_key=body.api_key)
        try:
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=16,
                messages=[{"role": "user", "content": "ping"}],
            )
        except Exception as e:
            raise HTTPException(400, f"Claude API test failed: {e}")
        s = load_settings()
        s["claude_api_key"] = body.api_key
        save_settings(s)
        return {"ok": True}

    @app.post("/api/onboarding/complete")
    def complete_onboarding() -> dict:
        s = load_settings()
        s["onboarded"] = True
        save_settings(s)
        return {"ok": True}

    @app.get("/api/gmail/sample")
    def gmail_sample() -> dict:
        return {"connected": gmail_obs.is_connected(), "subjects": gmail_obs.sample_recent_subjects()}

    dist = find_frontend_dist()
    if dist:
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(dist / "index.html")
    else:
        @app.get("/")
        def index_placeholder() -> dict:
            return {
                "message": "Frontend not built. Run `npm install && npm run build` in frontend/",
                "api_status": "/api/status",
            }

    @app.on_event("startup")
    async def _start_observers() -> None:
        asyncio.create_task(window_obs.sample_loop())

    return app
