"""macOS active-window screenshot + Apple Vision OCR. No-op elsewhere.

CGWindowListCreateImage captures the frontmost app's window into a CGImage,
Vision's VNRecognizeTextRequest extracts text, image is released. Text is
deduped by hash so we don't record the same screen repeatedly.
"""
import asyncio
import hashlib
import sys
from typing import Optional

from ..storage import record_event

MAX_TEXT_CHARS = 4000
_last_hash: Optional[str] = None


async def sample_loop(interval: float = 30.0) -> None:
    if sys.platform != "darwin":
        return
    loop = asyncio.get_running_loop()
    while True:
        try:
            result = await loop.run_in_executor(None, _capture_and_ocr)
            if result:
                _maybe_record(result)
        except Exception as e:
            record_event("ocr", "error", {"message": str(e)})
        await asyncio.sleep(interval)


def _maybe_record(result: dict) -> None:
    global _last_hash
    text = result.get("text") or ""
    if not text.strip():
        return
    h = hashlib.md5(text.encode("utf-8")).hexdigest()
    if h == _last_hash:
        return
    _last_hash = h
    record_event(
        "ocr",
        "active_window",
        {
            "app": result.get("app"),
            "title": result.get("title"),
            "text": text[:MAX_TEXT_CHARS],
            "truncated": len(text) > MAX_TEXT_CHARS,
        },
    )


def _capture_and_ocr() -> Optional[dict]:
    try:
        import Quartz
        import Vision
        from AppKit import NSWorkspace
    except ImportError:
        return None

    front = NSWorkspace.sharedWorkspace().frontmostApplication()
    if front is None:
        return None
    app_name = front.localizedName()
    pid = int(front.processIdentifier())

    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
        Quartz.kCGNullWindowID,
    )
    target_id = None
    title = None
    for w in windows:
        if w.get("kCGWindowOwnerPID") == pid and w.get("kCGWindowLayer", 0) == 0:
            target_id = w.get("kCGWindowNumber")
            title = w.get("kCGWindowName") or title
            break
    if target_id is None:
        return None

    image = Quartz.CGWindowListCreateImage(
        Quartz.CGRectNull,
        Quartz.kCGWindowListOptionIncludingWindow,
        target_id,
        Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution,
    )
    if image is None:
        return None

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)

    success, _err = handler.performRequests_error_([request], None)
    if not success:
        return None

    parts: list[str] = []
    for obs in request.results() or []:
        cands = obs.topCandidates_(1)
        if cands and len(cands) > 0:
            parts.append(str(cands[0].string()))
    text = "\n".join(parts)
    return {"app": app_name, "title": title, "text": text}
