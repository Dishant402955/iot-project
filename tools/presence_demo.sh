#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="$ROOT/vendor/.venv/bin/python"
DEMO="$ROOT/tools/live_presence_model_demo.py"
MODEL="$ROOT/models/presence_temporal_extra_trees_dev_v1.joblib"

usage() {
  cat <<'USAGE'
Usage: tools/presence_demo.sh [live|once|step]

  live  Continuously capture CSI and run temporal Extra Trees (default).
  once  Capture one 50-attempt batch, run inference once, then exit.
  step  Capture one batch, show its prediction, then wait for Enter before continuing.

The model prints an experimental PRESENT/ABSENT prediction. It is NOT a
validated occupancy detector. Run only at the physical laptop console.
Wi-Fi is briefly interrupted during each CSI capture batch.
USAGE
}
MODE="${1:-live}"
case "$MODE" in
  live) ARGS=() ;;
  once) ARGS=(--once) ;;
  step) ARGS=(--step) ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
[[ "$#" -le 1 ]] || { usage >&2; exit 2; }
if [[ "$EUID" -ne 0 ]]; then exec sudo -- "$0" "$MODE"; fi
[[ -x "$PYTHON" ]] || { echo "ERROR: virtualenv Python missing: $PYTHON" >&2; exit 1; }
[[ -f "$DEMO" ]] || { echo "ERROR: model demo missing: $DEMO" >&2; exit 1; }
[[ -f "$MODEL" ]] || { echo "ERROR: temporal Extra Trees demo model missing: $MODEL" >&2; exit 1; }
echo "Starting live CSI inference with the development temporal Extra Trees. No training or calibration will occur."
exec "$PYTHON" "$DEMO" "${ARGS[@]}"
