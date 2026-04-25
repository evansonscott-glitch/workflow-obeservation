"""macOS menu-bar status icon. No-op on other platforms."""
import sys
import threading
import webbrowser

from .config import HOST, PORT


def run_menubar(stop_event: threading.Event) -> None:
    if sys.platform != "darwin":
        return
    try:
        import rumps
    except ImportError:
        return

    url = f"http://{HOST}:{PORT}/"

    class App(rumps.App):
        def __init__(self) -> None:
            super().__init__("Workflow Observer", title="WO", quit_button=None)
            self.menu = ["Open dashboard", "Pause", None, "Quit"]

        @rumps.clicked("Open dashboard")
        def open_dashboard(self, _: object) -> None:
            webbrowser.open(url)

        @rumps.clicked("Pause")
        def pause(self, sender: object) -> None:
            sender.title = "Resume" if sender.title == "Pause" else "Pause"

        @rumps.clicked("Quit")
        def quit_app(self, _: object) -> None:
            stop_event.set()
            rumps.quit_application()

    App().run()
