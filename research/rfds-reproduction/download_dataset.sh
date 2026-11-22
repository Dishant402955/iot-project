#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/.venv-rfds/bin/python"
DEST="$ROOT/data/rfds-reference"
[[ -x "$PY" ]] || { echo "Run bootstrap.sh first." >&2; exit 2; }
"$ROOT/.venv-rfds/bin/hf" download JessicaSanson/Wi-Fi_Monostatic_Human_Sensing_CSI_Intel \
  --repo-type dataset --local-dir "$DEST" --max-workers 2
