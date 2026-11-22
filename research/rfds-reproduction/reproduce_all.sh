#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$ROOT/.venv-rfds/bin/python"
DATA="$ROOT/data/rfds-reference"
OUT="$ROOT/research/rfds-reproduction/outputs"
[[ -x "$PY" ]] || { echo "Missing environment. Run research/rfds-reproduction/bootstrap.sh" >&2; exit 2; }
mkdir -p "$OUT"
"$PY" "$ROOT/research/rfds-reproduction/validate_dataset.py" --root "$DATA" --output "$OUT/dataset_validation.json"
"$PY" -m unittest discover -s "$ROOT/research/rfds-reproduction/tests" -v
for session in walking_HP walking_LENOVO Breathing_HP; do
  "$PY" "$ROOT/research/rfds-reproduction/run_dataset.py" "$DATA/$session/csi.csv" --output-dir "$OUT"
done
for session in walking_HP walking_LENOVO; do
  "$PY" "$ROOT/research/rfds-reproduction/evaluate_labels.py" \
    --labels "$DATA/$session/labels.csv" \
    --decisions "$OUT/${session}_decisions.csv" \
    --output "$OUT/${session}_rfds_metrics.json"
  "$PY" "$ROOT/research/rfds-reproduction/baseline.py" \
    "$DATA/$session/csi.csv" \
    --report "$OUT/${session}_baseline_metrics.json" \
    --train-model "$OUT/${session}_baseline.joblib"
done
"$PY" "$ROOT/research/rfds-reproduction/cross_device.py" --root "$DATA" --output "$OUT/cross_device_metrics.json"
"$PY" - "$OUT/reproduction_manifest.json" <<'PY'
import json, platform, sys, time
from pathlib import Path
import numpy, pandas, scipy, matplotlib, sklearn, joblib
p=Path(sys.argv[1])
result={"created_unix":time.time(),"python":platform.python_version(),"platform":platform.platform(),
        "dependencies":{m.__name__:m.__version__ for m in [numpy,pandas,scipy,matplotlib,sklearn,joblib]},
        "note":"RF-DS and per-session baseline results are distinct. Read PROJECT_EXECUTION_PLAN.md before interpreting metrics."}
p.write_text(json.dumps(result,indent=2)+'\n')
PY
echo "Reproduction pipeline completed. Reports: $OUT"
