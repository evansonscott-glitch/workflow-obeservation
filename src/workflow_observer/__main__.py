import sys
import threading
import time
import webbrowser

import uvicorn

from .config import HOST, PORT
from .server import create_app


def _run_server(stop_event: threading.Event) -> None:
    config = uvicorn.Config(create_app(), host=HOST, port=PORT, log_level="info")
    server = uvicorn.Server(config)

    def watch() -> None:
        stop_event.wait()
        server.should_exit = True

    threading.Thread(target=watch, daemon=True).start()
    server.run()


def main() -> None:
    stop_event = threading.Event()

    server_thread = threading.Thread(target=_run_server, args=(stop_event,), daemon=True)
    server_thread.start()

    time.sleep(1.0)
    url = f"http://{HOST}:{PORT}/"
    print(f"Workflow Observer running at {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    if sys.platform == "darwin":
        from .menubar import run_menubar
        run_menubar(stop_event)
    else:
        try:
            server_thread.join()
        except KeyboardInterrupt:
            stop_event.set()


if __name__ == "__main__":
    main()
