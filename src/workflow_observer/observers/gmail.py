"""Gmail OAuth (desktop-app flow) and read helpers.

The user supplies their own credentials.json from a Google Cloud OAuth client
of type "Desktop app". InstalledAppFlow.run_local_server picks a free port
and Google accepts any localhost redirect for desktop clients.
"""
import json
import threading
from pathlib import Path
from typing import Optional

from ..config import app_support_dir

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_state = {"running": False, "error": None, "email": None}
_lock = threading.Lock()


def credentials_path() -> Path:
    return app_support_dir() / "gmail_credentials.json"


def token_path() -> Path:
    return app_support_dir() / "gmail_token.json"


def has_credentials() -> bool:
    return credentials_path().exists()


def is_connected() -> bool:
    return token_path().exists()


def save_credentials_json(content: str) -> None:
    parsed = json.loads(content)
    if "installed" not in parsed and "web" not in parsed:
        raise ValueError(
            "credentials.json must contain an 'installed' or 'web' key. "
            "Make sure you created a Desktop-app OAuth client."
        )
    credentials_path().write_text(content)


def connect_status() -> dict:
    with _lock:
        s = dict(_state)
    s["connected"] = is_connected()
    s["has_credentials"] = has_credentials()
    if s["connected"] and not s["email"]:
        s["email"] = _connected_email()
    return s


def _load_creds():
    if not is_connected():
        return None
    from google.oauth2.credentials import Credentials

    return Credentials.from_authorized_user_file(str(token_path()), SCOPES)


def _connected_email() -> Optional[str]:
    creds = _load_creds()
    if not creds:
        return None
    try:
        from googleapiclient.discovery import build

        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return service.users().getProfile(userId="me").execute().get("emailAddress")
    except Exception:
        return None


def start_oauth() -> None:
    """Run the OAuth flow in a background thread. Browser window opens to Google."""
    with _lock:
        if _state["running"]:
            return
        _state["running"] = True
        _state["error"] = None

    def run() -> None:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path()), SCOPES
            )
            creds = flow.run_local_server(port=0, open_browser=True)
            token_path().write_text(creds.to_json())
            email = _connected_email()
            with _lock:
                _state["email"] = email
        except Exception as e:
            with _lock:
                _state["error"] = str(e)
        finally:
            with _lock:
                _state["running"] = False

    threading.Thread(target=run, daemon=True).start()


def disconnect() -> None:
    p = token_path()
    if p.exists():
        p.unlink()
    with _lock:
        _state["email"] = None
        _state["error"] = None


def sample_recent_subjects(limit: int = 5) -> list[str]:
    creds = _load_creds()
    if not creds:
        return []
    from googleapiclient.discovery import build

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)
    resp = service.users().messages().list(userId="me", maxResults=limit).execute()
    out: list[str] = []
    for m in resp.get("messages", []):
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=m["id"], format="metadata", metadataHeaders=["Subject"])
            .execute()
        )
        for h in msg.get("payload", {}).get("headers", []):
            if h["name"] == "Subject":
                out.append(h["value"])
                break
    return out
