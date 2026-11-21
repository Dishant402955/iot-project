#!/usr/bin/env bash
# Repeated, bounded RTL8821CE PCIe LA capture + temporal CSI extraction.
# Run locally: sudo bash tools/rtl8821ce_pcie_la_capture.sh [channel]
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BDF="${WIFI_PRESENCE_BDF:-0000:01:00.0}"
CHANNEL="${1:-${WIFI_PRESENCE_CHANNEL:-}}"
DEV="$ROOT/vendor/devourer"
BIND="$DEV/tests/pcie_vfio_bind.sh"
RX="$DEV/build-rtl8821ce-pcie/rxdemo"
PY="$ROOT/vendor/.venv/bin/python"
CSI="$DEV/tools/la_csi_series.py"
CAPTURE_COUNT="${WIFI_PRESENCE_CAPTURE_COUNT:-30}"
CAPTURE_INTERVAL_MS="${WIFI_PRESENCE_CAPTURE_INTERVAL_MS:-1000}"
RUN_TIMEOUT="${WIFI_PRESENCE_CAPTURE_TIMEOUT_SEC:-120}"
LA_TRIGGER="${WIFI_PRESENCE_LA_TRIGGER:-cca}"
LA_POST_TRIGGER_US="${WIFI_PRESENCE_LA_POST_TRIGGER_US:-200}"

usage() {
  echo "Usage: sudo bash $0 [channel]" >&2
  echo "Default channel: auto-detected from the currently connected wlp1s0 link." >&2
  echo "Defaults: CCA trigger, 200 us post-trigger, 30 captures, 1000 ms interval." >&2
  echo "Override trigger/time with WIFI_PRESENCE_LA_TRIGGER and WIFI_PRESENCE_LA_POST_TRIGGER_US." >&2
  echo "Override count/interval with WIFI_PRESENCE_CAPTURE_COUNT and WIFI_PRESENCE_CAPTURE_INTERVAL_MS." >&2
  echo "Override PCI BDF with WIFI_PRESENCE_BDF." >&2
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then usage; exit 0; fi
if [[ "$EUID" -ne 0 ]]; then
  echo "ERROR: run with sudo; this operation temporarily takes ownership of the Wi-Fi PCIe adapter." >&2
  usage
  exit 2
fi

for path in "$BIND" "$RX" "$PY" "$CSI"; do
  if [[ ! -e "$path" ]]; then echo "ERROR: required project file missing: $path" >&2; exit 2; fi
done
if [[ ! -x "$RX" || ! -x "$PY" ]]; then
  echo "ERROR: rxdemo or project Python is not executable." >&2; exit 2
fi
if ! "$PY" -c 'import numpy' >/dev/null 2>&1; then
  echo "ERROR: NumPy is unavailable in the project-local Python environment." >&2; exit 2
fi

if ! [[ "$CAPTURE_COUNT" =~ ^[0-9]+$ ]] || (( CAPTURE_COUNT < 2 || CAPTURE_COUNT > 50 )); then
  echo "ERROR: capture count must be between 2 and 50." >&2; exit 2
fi
if ! [[ "$CAPTURE_INTERVAL_MS" =~ ^[0-9]+$ ]] || (( CAPTURE_INTERVAL_MS < 100 || CAPTURE_INTERVAL_MS > 10000 )); then
  echo "ERROR: capture interval must be between 100 and 10000 ms." >&2; exit 2
fi


case "$LA_TRIGGER" in
  cca|crcok|crcfail) ;;
  *) echo "ERROR: LA trigger must be one of: cca, crcok, crcfail." >&2; exit 2 ;;
esac
if ! [[ "$LA_POST_TRIGGER_US" =~ ^[0-9]+$ ]] || (( LA_POST_TRIGGER_US < 20 || LA_POST_TRIGGER_US > 380 )); then
  echo "ERROR: post-trigger time must be between 20 and 380 us for the 8192-sample window." >&2
  exit 2
fi

# Default to the channel the laptop is already using. This is read-only and
# happens before VFIO takes the adapter; never guess a stale channel number.
if [[ -z "$CHANNEL" ]]; then
  FREQ_GHZ="$(iwconfig wlp1s0 2>/dev/null | sed -n 's/.*Frequency:\([0-9.]*\) GHz.*/\1/p' | head -n1)"
  if [[ -z "$FREQ_GHZ" ]]; then
    echo "ERROR: could not read the current wlp1s0 frequency. Pass an explicit channel." >&2
    exit 2
  fi
  CHANNEL="$(awk -v ghz="$FREQ_GHZ" 'BEGIN {
    f = ghz * 1000
    if (f >= 2400 && f < 2500) c = int((f - 2407) / 5 + 0.5)
    else if (f >= 5000 && f < 5925) c = int((f - 5000) / 5 + 0.5)
    else if (f >= 5925 && f <= 7125) c = int((f - 5950) / 5 + 0.5)
    else exit 1
    if (c > 0) print c; else exit 1
  }')" || {
    echo "ERROR: could not map current Wi-Fi frequency $FREQ_GHZ GHz to a channel; pass an explicit channel." >&2
    exit 2
  }
fi

case "$CHANNEL" in
  1|2|3|4|5|6|7|8|9|10|11|12|13|14|36|40|44|48|52|56|60|64|100|104|108|112|116|120|124|128|132|136|140|144|149|153|157|161|165) ;;
  *) echo "ERROR: channel '$CHANNEL' is not in this script's conservative channel allowlist." >&2; exit 2 ;;
esac

SYSDEV="/sys/bus/pci/devices/$BDF"
if [[ ! -d "$SYSDEV" ]]; then echo "ERROR: PCI device $BDF does not exist." >&2; exit 2; fi
VENDOR="$(<"$SYSDEV/vendor")"
DEVICE="$(<"$SYSDEV/device")"
if [[ "$VENDOR:$DEVICE" != "0x10ec:0xc821" ]]; then
  echo "ERROR: expected RTL8821CE 10ec:c821 at $BDF, found $VENDOR:$DEVICE." >&2
  exit 2
fi
if [[ ! -e "$SYSDEV/iommu_group" ]]; then
  echo "ERROR: $BDF has no IOMMU group; refusing VFIO operation." >&2
  exit 2
fi
current_driver() {
  if [[ -e "$SYSDEV/driver" ]]; then basename "$(readlink -f "$SYSDEV/driver")"; else echo none; fi
}
DRIVER_BEFORE="$(current_driver)"
case "$DRIVER_BEFORE" in
  rtw_8821ce) ;;
  *) echo "ERROR: expected the normal rtw_8821ce driver, found '$DRIVER_BEFORE'. Refusing to change an unexpected driver." >&2; exit 2 ;;
esac

source "$ROOT/tools/devourer_env.sh"
OUT_DIR="$(mktemp -d /tmp/rtl8821ce-la.XXXXXX)" || exit 2
CAPTURE_BASE="$OUT_DIR/capture.bin"
LOG="$OUT_DIR/rxdemo.log"
CSI_SERIES="$OUT_DIR/csi_series.jsonl"
RESTORE_NEEDED=1

cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  if [[ "$RESTORE_NEEDED" == 1 ]]; then
    echo
    echo "[cleanup] Restoring $BDF to the normal kernel driver..."
    if ! bash "$BIND" "$BDF" --restore; then
      echo "CRITICAL: automatic restore failed. Run: sudo bash '$BIND' '$BDF' --restore" >&2
      rc=1
    fi
    RESTORE_NEEDED=0
  fi
  if [[ -n "${SUDO_USER:-}" && -d "$OUT_DIR" ]]; then
    chown -R "$SUDO_USER:$(id -gn "$SUDO_USER")" "$OUT_DIR" 2>/dev/null || true
    chmod -R u+rwX "$OUT_DIR" 2>/dev/null || true
  fi
  echo "Artifacts: $OUT_DIR"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cat <<MSG
RTL8821CE PCIe LA capture
  PCI device : $BDF (10ec:c821)
  driver now : $DRIVER_BEFORE
  channel    : $CHANNEL / 20 MHz
  trigger    : $LA_TRIGGER (ambient channel activity)
  LA mode    : 20 Msps, dma0, BB debug port 0x880
  captures   : $CAPTURE_COUNT
  interval   : $CAPTURE_INTERVAL_MS ms between captures
  buffer     : full 8192-sample ring; $LA_POST_TRIGGER_US us post-trigger
  output     : $OUT_DIR/capture.NNNN.bin
  CSI series : $CSI_SERIES

The adapter's normal Wi-Fi connection will be unavailable during this run.
The script does NOT restart NetworkManager or reboot the machine. It restores
rtw_8821ce before exit. Run locally at the machine's physical console.
No firmware flash, persistent binding, or system configuration change is performed.
MSG

bash "$BIND" "$BDF" || exit $?

# Repeated captures happen in one rxdemo process and one VFIO ownership window.
# SIGINT is sent only after the requested successful-capture count is reached.
# A hard deadline and TERM fallback prevent a stuck RX loop from blocking driver restore.
RX_ENV=(
  DEVOURER_PCIE_BDF="$BDF"
  DEVOURER_CHANNEL="$CHANNEL"
  DEVOURER_BW=20
  DEVOURER_LOG_LEVEL=debug
  DEVOURER_LA_DELAY_MS=2000
  DEVOURER_LA_CAPTURE="$LA_TRIGGER/20M/dma0/port:0x880/t$LA_POST_TRIGGER_US/all"
  DEVOURER_LA_OUT="$CAPTURE_BASE"
  DEVOURER_LA_MAX=8192
  DEVOURER_LA_COUNT="$CAPTURE_COUNT"
  DEVOURER_LA_INTERVAL_MS="$CAPTURE_INTERVAL_MS"
)
env "${RX_ENV[@]}" "$RX" >"$LOG" 2>&1 &
RX_PID=$!
STOP_SENT=0
rx_is_running() {
  local state
  state="$(ps -o stat= -p "$RX_PID" 2>/dev/null | tr -d ' ')"
  [[ -n "$state" && "$state" != Z* ]]
}
for ((tick=0; tick<RUN_TIMEOUT*4; tick++)); do
  if ! rx_is_running; then break; fi
  SUCCESS_COUNT="$("$PY" - "$LOG" <<'PYCOUNT'
import json, sys
n = 0
try:
    for line in open(sys.argv[1], errors="replace"):
        try: e = json.loads(line)
        except json.JSONDecodeError: continue
        n += e.get("ev") == "la.capture" and e.get("ok") == 1
except FileNotFoundError: pass
print(n)
PYCOUNT
)"
  if (( SUCCESS_COUNT >= CAPTURE_COUNT )); then
    echo "Captured $SUCCESS_COUNT/$CAPTURE_COUNT; stopping RX cleanly..."
    kill -INT "$RX_PID" 2>/dev/null || true
    STOP_SENT=1
    break
  fi
  if grep -Eq '"ev":"la\.(wedged|timeout|nosupport)"|"ev":"la\.capture".*"ok":0' "$LOG" 2>/dev/null; then
    echo "ERROR: LA capture reported a hardware, trigger, or output failure; stopping sequence." >&2
    kill -INT "$RX_PID" 2>/dev/null || true
    STOP_SENT=1
    break
  fi
  sleep 0.25
done
if (( STOP_SENT == 0 )) && rx_is_running; then
  echo "Capture deadline reached; requesting graceful RX shutdown." >&2
  kill -INT "$RX_PID" 2>/dev/null || true
fi
for ((tick=0;tick<40;tick++)); do
  rx_is_running || break
  sleep 0.25
done
if rx_is_running; then
  echo "RX did not stop after SIGINT; escalating to SIGTERM." >&2
  kill -TERM "$RX_PID" 2>/dev/null || true
  for ((tick=0;tick<20;tick++)); do
    rx_is_running || break
    sleep 0.25
  done
fi
if rx_is_running; then
  echo "CRITICAL: RX process ignored SIGINT/SIGTERM; forcing exit so driver restoration can proceed." >&2
  kill -KILL "$RX_PID" 2>/dev/null || true
fi
wait "$RX_PID"
RX_STATUS=$?
cat "$LOG"
if [[ "$RX_STATUS" -ne 0 ]]; then
  echo "ERROR: rxdemo exited with status $RX_STATUS. Raw log: $LOG" >&2
  exit 1
fi

# Validate every event-backed dump before attempting CSI extraction.
if ! "$PY" - "$LOG" "$CAPTURE_COUNT" <<'PYVALIDATE'
import json, os, struct, sys
log_path, expected = sys.argv[1], int(sys.argv[2])
events = []
with open(log_path, errors="replace") as f:
    for line in f:
        try: events.append(json.loads(line))
        except json.JSONDecodeError: pass
if any(e.get("ev") == "la.wedged" for e in events):
    raise SystemExit("FAIL: device reported la.wedged")
successes = [e for e in events if e.get("ev") == "la.capture" and e.get("ok") == 1]
if len(successes) != expected:
    raise SystemExit(f"FAIL: expected {expected} successful captures, got {len(successes)}")
seen = set()
usable_iq = 0
for event in successes:
    path = event.get("file")
    if not path or path in seen: raise SystemExit(f"FAIL: missing/duplicate output path: {path}")
    seen.add(path)
    if not os.path.isfile(path): raise SystemExit(f"FAIL: missing capture file: {path}")
    with open(path, "rb") as f:
        hdr = f.read(32)
        if len(hdr) != 32 or hdr[:4] != b"DVLA": raise SystemExit(f"FAIL: invalid DVLA header: {path}")
        version = hdr[4]
        n = struct.unpack_from("<I", hdr, 12)[0]
        data = f.read()
    if version != 1 or n <= 0 or len(data) != 8*n:
        raise SystemExit(f"FAIL: malformed dump {path} (version={version}, samples={n}, bytes={len(data)})")
    if event.get("samples") != n: raise SystemExit(f"FAIL: sample count mismatch: {path}")
    unique_words = len(set(struct.unpack(f"<{n}Q", data)))
    if unique_words < 2:
        print(f"IQ_CAPTURE_WARN: {os.path.basename(path)} has a constant sample buffer; retaining it but excluding it from CSI")
        continue
    usable_iq += 1
    print(f"IQ_CAPTURE_PASS: {os.path.basename(path)} samples={n} bytes={32+len(data)} unique_words={unique_words} event_t={event.get('t')}")
if usable_iq < 2:
    raise SystemExit(f"FAIL: only {usable_iq} captures contain varying IQ samples; need at least 2")
print(f"IQ_SEQUENCE_PASS: {len(successes)} structurally valid captures; {usable_iq} contain varying IQ samples")
PYVALIDATE
then
  echo "ERROR: repeated IQ validation failed. Raw log: $LOG" >&2
  exit 1
fi

shopt -s nullglob
CAPTURE_FILES=("$OUT_DIR"/capture.*.bin)
if ! "$PY" "$CSI" "${CAPTURE_FILES[@]}" --events-log "$LOG" \
    --output "$CSI_SERIES" --min-captures 2; then
  echo "ERROR: CSI time-series extraction failed. Raw IQ files and log retained in $OUT_DIR" >&2
  exit 1
fi

echo "Capture complete. Raw IQ files: $OUT_DIR/capture.NNNN.bin"
echo "Temporal CSI series: $CSI_SERIES"
echo "Capture log: $LOG"
