"""Gmail OAuth + read stub. Real OAuth flow wired during onboarding."""
from pathlib import Path

from ..config import app_support_dir

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def credentials_path() -> Path:
    return app_support_dir() / "gmail_credentials.json"


def token_path() -> Path:
    return app_support_dir() / "gmail_token.json"


def is_connected() -> bool:
    return token_path().exists()


def sample_recent_subjects(limit: int = 5) -> list[str]:
    """Used by the onboarding 'verify connection' step. Returns subjects only."""
    if not is_connected():
        return []
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        return []

    creds = Credentials.from_authorized_user_file(str(token_path()), SCOPES)
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
