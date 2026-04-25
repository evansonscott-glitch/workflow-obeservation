"""py2app build config. Run on macOS: python setup.py py2app"""
from setuptools import find_packages, setup

APP = ["src/workflow_observer/__main__.py"]

# Place the built frontend at <bundle>/Contents/Resources/frontend/dist/
DATA_FILES = [("frontend", ["frontend/dist"])]

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
    "packages": ["workflow_observer", "anthropic", "fastapi", "uvicorn", "starlette", "pydantic"],
    "includes": [
        "rumps",
        "websockets",
        "google.auth",
        "google.oauth2",
        "google_auth_oauthlib",
        "googleapiclient",
    ],
}

setup(
    app=APP,
    name="WorkflowObserver",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={"workflow_observer": ["templates/*.py"]},
    include_package_data=True,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
