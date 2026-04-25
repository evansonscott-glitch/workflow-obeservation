import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__, packager
from .analysis import agent_designer, segmenter
from .observers import browser as browser_obs
from .observers import gmail as gmail_obs
from .observers import ocr as ocr_obs
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

    class GmailCredentials(BaseModel):
        content: str

    @app.post("/api/gmail/credentials")
    def gmail_upload_credentials(body: GmailCredentials) -> dict:
        try:
            gmail_obs.save_credentials_json(body.content)
        except Exception as e:
            raise HTTPException(400, str(e))
        return {"ok": True}

    @app.post("/api/gmail/connect")
    def gmail_connect() -> dict:
        if not gmail_obs.has_credentials():
            raise HTTPException(400, "Upload credentials.json first.")
        gmail_obs.start_oauth()
        return {"ok": True}

    @app.get("/api/gmail/connect/status")
    def gmail_connect_status() -> dict:
        return gmail_obs.connect_status()

    @app.post("/api/gmail/disconnect")
    def gmail_disconnect() -> dict:
        gmail_obs.disconnect()
        return {"ok": True}

    class SegmentBody(BaseModel):
        start_ts: Optional[float] = None
        end_ts: Optional[float] = None
        hours_back: Optional[float] = None

    @app.post("/api/segment")
    async def segment(body: SegmentBody) -> dict:
        end = body.end_ts or time.time()
        if body.start_ts is not None:
            start = body.start_ts
        elif body.hours_back is not None:
            start = end - body.hours_back * 3600
        else:
            start = end - 4 * 3600
        try:
            return await asyncio.to_thread(segmenter.segment_window, start, end)
        except Exception as e:
            raise HTTPException(500, str(e))

    @app.get("/api/workflows")
    def workflows_list(limit: int = 50) -> list[dict]:
        return segmenter.list_workflows(limit)

    class FlagBody(BaseModel):
        flagged: bool

    @app.post("/api/workflows/{wid}/flag")
    def workflow_flag(wid: int, body: FlagBody) -> dict:
        segmenter.set_flag(wid, body.flagged)
        return {"ok": True}

    class DesignBody(BaseModel):
        workflow_id: int

    @app.post("/api/agents/design")
    async def agents_design(body: DesignBody) -> dict:
        try:
            return await asyncio.to_thread(agent_designer.design_agent, body.workflow_id)
        except Exception as e:
            raise HTTPException(500, str(e))

    class AgentBody(BaseModel):
        spec: dict

    @app.post("/api/agents")
    def agents_create(body: AgentBody) -> dict:
        agent_id = agent_designer.save_agent(body.spec)
        return {"id": agent_id}

    @app.get("/api/agents")
    def agents_list() -> list[dict]:
        return agent_designer.list_agents()

    @app.get("/api/agents/{agent_id}")
    def agents_get(agent_id: int) -> dict:
        agent = agent_designer.get_agent(agent_id)
        if not agent:
            raise HTTPException(404, "Agent not found")
        return agent

    @app.put("/api/agents/{agent_id}")
    def agents_update(agent_id: int, body: AgentBody) -> dict:
        agent_designer.update_agent(agent_id, body.spec)
        return {"ok": True}

    class ModeBody(BaseModel):
        mode: str

    @app.post("/api/agents/{agent_id}/mode")
    def agents_mode(agent_id: int, body: ModeBody) -> dict:
        try:
            agent_designer.set_mode(agent_id, body.mode)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"ok": True}

    @app.delete("/api/agents/{agent_id}")
    def agents_delete(agent_id: int) -> dict:
        agent_designer.delete_agent(agent_id)
        return {"ok": True}

    class ExportBody(BaseModel):
        agent_ids: Optional[list[int]] = None
        dest: Optional[str] = None

    @app.post("/api/export")
    def export_to_dir(body: ExportBody) -> dict:
        dest = Path(body.dest).expanduser() if body.dest else packager.default_export_dir()
        try:
            return packager.package_to_dir(dest, body.agent_ids)
        except RuntimeError as e:
            raise HTTPException(400, str(e))

    @app.get("/api/export.zip")
    def export_zip(agent_ids: Optional[str] = None) -> Response:
        ids: Optional[list[int]] = None
        if agent_ids:
            try:
                ids = [int(x) for x in agent_ids.split(",") if x.strip()]
            except ValueError:
                raise HTTPException(400, "agent_ids must be comma-separated integers")
        try:
            blob = packager.package_to_zip(ids)
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        return Response(
            content=blob,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="agents-export.zip"'},
        )

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
        asyncio.create_task(ocr_obs.sample_loop())

    return app
