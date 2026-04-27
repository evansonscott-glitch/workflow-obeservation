#!/usr/bin/env bash
# Build Workflow Observer .app + .dmg locally on macOS.
# Result: dist/WorkflowObserver.dmg
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ "$(uname)" != "Darwin" ]]; then
  echo "This build must be run on macOS (py2app + hdiutil are macOS-only)." >&2
  exit 1
fi

PY="${PY:-}"
if [[ -z "$PY" ]]; then
  for candidate in python3.13 python3.12 python3.11; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PY="$candidate"
      break
    fi
  done
fi

if [[ -z "$PY" ]] || ! "$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "ERROR: need Python 3.11 or newer." >&2
  echo "Install from https://www.python.org/downloads/ then re-run." >&2
  exit 1
fi

echo "==> using $PY ($("$PY" --version))"

echo "==> cleaning previous build"
rm -rf build dist

echo "==> building frontend"
pushd frontend >/dev/null
if [[ ! -d node_modules ]]; then
  if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
fi
npm run build
popd >/dev/null

echo "==> setting up venv"
if [[ -d .venv ]] && ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "    existing .venv uses an incompatible Python — recreating"
  rm -rf .venv
fi
if [[ ! -d .venv ]]; then
  "$PY" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -e ".[dev]"

echo "==> running py2app"
python setup.py py2app

APP="dist/WorkflowObserver.app"
if [[ ! -d "$APP" ]]; then
  echo "py2app did not produce $APP" >&2
  exit 1
fi

echo "==> ad-hoc signing the bundle"
codesign --force --deep --sign - "$APP"

echo "==> creating DMG"
STAGING="dist/dmg-staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

DMG="dist/WorkflowObserver.dmg"
rm -f "$DMG"
hdiutil create -volname "Workflow Observer" -srcfolder "$STAGING" -ov -format UDZO "$DMG" >/dev/null

rm -rf "$STAGING"

SIZE=$(du -h "$DMG" | cut -f1)
echo ""
echo "✓ Built $DMG ($SIZE)"
echo ""
echo "Install:"
echo "  1. open $DMG"
echo "  2. drag Workflow Observer to Applications"
echo "  3. first launch: right-click the app → Open → confirm"
echo "     (unsigned apps need this once; subsequent launches are normal)"
