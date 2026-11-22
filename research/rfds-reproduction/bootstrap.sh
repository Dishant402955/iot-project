#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="$ROOT/.venv-rfds"
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install uv from https://docs.astral.sh/uv/ before continuing." >&2
  exit 2
fi
uv venv --python "$PYTHON_VERSION" "$VENV"
uv pip install --python "$VENV/bin/python" -r "$ROOT/research/rfds-reproduction/requirements.lock.txt"
echo "Environment ready: $VENV"
