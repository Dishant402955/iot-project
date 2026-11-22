#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv-rfds"
DEST="$ROOT/data/rfds-reference"
if [[ ! -x "$VENV/bin/hf" ]]; then
  echo "Missing .venv-rfds. Create it with: uv venv --python 3.12 .venv-rfds && uv pip install --python .venv-rfds/bin/python huggingface_hub"
  exit 1
fi
mkdir -p "$DEST"
"$VENV/bin/hf" download JessicaSanson/Wi-Fi_Monostatic_Human_Sensing_CSI_Intel \
  --repo-type dataset --local-dir "$DEST" --max-workers 2
