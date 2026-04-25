"""py2app build config. Run on macOS: python setup.py py2app"""
from setuptools import setup

APP = ["src/workflow_observer/__main__.py"]
DATA_FILES = [("frontend_dist", ["frontend/dist"])]
OPTIONS = {
    "argv_emulation": False,
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "Workflow Observer",
        "CFBundleDisplayName": "Workflow Observer",
        "CFBundleIdentifier": "com.philoventures.workflow-observer",
        "CFBundleVersion": "0.1.0",
        "CFBundleShortVersionString": "0.1.0",
        "NSAppleEventsUsageDescription": "Used to track which apps and windows you use.",
        "NSScreenCaptureUsageDescription": "Used to OCR active-window content; images are discarded.",
    },
    "packages": ["workflow_observer"],
    "includes": ["rumps", "fastapi", "uvicorn", "anthropic"],
}

setup(
    app=APP,
    name="WorkflowObserver",
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
