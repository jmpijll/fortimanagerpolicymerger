#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
ROOT_DIR=$(cd "$SCRIPT_DIR/.." && pwd)

VENV_BIN="$ROOT_DIR/.venv/bin"
PY="$VENV_BIN/python"
PIP="$VENV_BIN/pip"

APP_ENTRY="policy_merger/gui/main.py"
DIST_DIR="$ROOT_DIR/dist"

export PYTHONPATH="$ROOT_DIR/src"

"$PIP" install pyinstaller >/dev/null
"$VENV_BIN/pyinstaller" \
  --noconfirm \
  --clean \
  --windowed \
  --qt-plugins platforms,styles,imageformats \
  --name PolicyMerger \
  "$ROOT_DIR/src/$APP_ENTRY"

echo "Built artifacts in: $DIST_DIR"


