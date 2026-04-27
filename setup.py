"""py2app build config. Run on macOS: python setup.py py2app

Runtime dependencies live in requirements.txt — keeping them OUT of setup.py
and out of pyproject.toml's [project] table is what stops py2app from erroring
with `install_requires is no longer supported`.
"""
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
    description="Observe how you work on a Mac and generate Claude Code agents.",
    python_requires=">=3.11",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    package_data={"workflow_observer": ["templates/*.py"]},
    include_package_data=True,
    data_files=DATA_FILES,
    entry_points={
        "console_scripts": [
            "workflow-observer = workflow_observer.__main__:main",
        ],
    },
    options={"py2app": OPTIONS},
)
