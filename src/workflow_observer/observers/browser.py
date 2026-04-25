"""WebSocket sink for the Chrome extension."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..storage import record_event

router = APIRouter()


@router.websocket("/ws/browser")
async def browser_ws(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            msg = await ws.receive_json()
            kind = msg.get("kind", "tab")
            record_event("browser", kind, msg.get("payload", {}))
    except WebSocketDisconnect:
        return
