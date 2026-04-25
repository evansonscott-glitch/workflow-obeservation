import os
import sys
from pathlib import Path


def app_support_dir() -> Path:
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "WorkflowObserver"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "workflow-observer"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return app_support_dir() / "events.sqlite"


def settings_path() -> Path:
    return app_support_dir() / "settings.json"


HOST = "127.0.0.1"
PORT = 8765
