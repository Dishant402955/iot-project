#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/.venv-rfds/bin/python"
[[ -x "$PY" ]] || { echo "Missing .venv-rfds; run research/rfds-reproduction/bootstrap.sh" >&2; exit 2; }
"$PY" - <<'PY'
import numpy, pandas, scipy, matplotlib, sklearn, joblib
for module in (numpy, pandas, scipy, matplotlib, sklearn, joblib):
    print(f"{module.__name__}: {module.__version__}")
PY
"$PY" -m unittest discover -s "$ROOT/research/rfds-reproduction/tests" -v
"$PY" "$ROOT/research/rfds-reproduction/validate_dataset.py" --root "$ROOT/data/rfds-reference"
