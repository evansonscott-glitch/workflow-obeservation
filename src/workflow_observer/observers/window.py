"""macOS active window/app sampler. No-op on other platforms."""
import asyncio
import sys

from ..storage import record_event


async def sample_loop(interval: float = 3.0) -> None:
    if sys.platform != "darwin":
        return
    try:
        from AppKit import NSWorkspace
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListOptionOnScreenOnly,
        )
    except ImportError:
        return

    last_signature = None
    while True:
        ws = NSWorkspace.sharedWorkspace()
        front = ws.frontmostApplication()
        app_name = front.localizedName() if front else None
        bundle_id = front.bundleIdentifier() if front else None

        title = None
        windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
        for w in windows:
            if w.get("kCGWindowOwnerName") == app_name:
                title = w.get("kCGWindowName") or title
                if title:
                    break

        signature = (app_name, title)
        if signature != last_signature:
            record_event(
                "window",
                "focus",
                {"app": app_name, "bundle_id": bundle_id, "title": title},
            )
            last_signature = signature

        await asyncio.sleep(interval)
