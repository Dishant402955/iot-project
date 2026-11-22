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
CAPTURE_COUNT="${WIFI_PRESENCE_CAPTURE_COUNT:-50}"
CAPTURE_INTERVAL_MS="${WIFI_PRESENCE_CAPTURE_INTERVAL_MS:-0}"
RUN_TIMEOUT="${WIFI_PRESENCE_CAPTURE_TIMEOUT_SEC:-180}"
LA_TRIGGER="${WIFI_PRESENCE_LA_TRIGGER:-cca}"
# This configures Realtek's MAC LA trigger-time register. It does NOT set
# the IQ sample count or capture-buffer duration. Keep old variable names as
# compatibility aliases, but prefer the accurately named setting.
LA_TRIGGER_TIME_US="${WIFI_PRESENCE_LA_TRIGGER_TIME_US:-${WIFI_PRESENCE_LA_CAPTURE_DURATION_US:-${WIFI_PRESENCE_LA_POST_TRIGGER_US:-20}}}"

usage() {
  echo "Usage: sudo bash $0 [channel]" >&2
  echo "Channel and target BSSID are read from the currently connected wlp1s0 link." >&2
  echo "Defaults: CCA trigger, 20 us MAC trigger-time setting, 50 captures, 0 ms re-arm delay." >&2
  echo "Diagnostic override: WIFI_PRESENCE_LA_TRIGGER=manual tests the LA engine without an RX trigger." >&2
  echo "Any supplied channel must match the active connection; it cannot retune the adapter." >&2
  echo "Override trigger timing with WIFI_PRESENCE_LA_TRIGGER_TIME_US (old aliases: WIFI_PRESENCE_LA_CAPTURE_DURATION_US, WIFI_PRESENCE_LA_POST_TRIGGER_US)." >&2
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

if ! [[ "$CAPTURE_COUNT" =~ ^[0-9]+$ ]] || (( CAPTURE_COUNT < 2 || CAPTURE_COUNT > 500 )); then
  echo "ERROR: capture count must be between 2 and 500." >&2; exit 2
fi
if ! [[ "$CAPTURE_INTERVAL_MS" =~ ^[0-9]+$ ]] || (( CAPTURE_INTERVAL_MS > 10000 )); then
  echo "ERROR: capture interval must be between 0 and 10000 ms." >&2; exit 2
fi


case "$LA_TRIGGER" in
  cca|crcok|crcfail|manual) ;;
  *) echo "ERROR: LA trigger must be one of: manual, cca, crcok, crcfail." >&2; exit 2 ;;
esac
if ! [[ "$LA_TRIGGER_TIME_US" =~ ^[0-9]+$ ]] || (( LA_TRIGGER_TIME_US < 1 || LA_TRIGGER_TIME_US > 8191 )); then
  echo "ERROR: MAC trigger-time setting must be between 1 and 8191 us (Realtek register encoding)." >&2
  exit 2
fi

# Read the active association before VFIO takes the only Wi-Fi adapter.
# We require a real BSSID and use the connected channel; an explicit channel
# argument is only accepted when it matches the active link.
WIFI_IFACE="${WIFI_PRESENCE_INTERFACE:-wlp1s0}"
IWCONFIG_OUTPUT="$(iwconfig "$WIFI_IFACE" 2>/dev/null || true)"
FREQ_GHZ="$(sed -n 's/.*Frequency:\([0-9.]*\) GHz.*/\1/p' <<<"$IWCONFIG_OUTPUT" | head -n1)"
TARGET_BSSID="$(sed -n 's/.*Access Point: \([0-9A-Fa-f:]*\).*/\1/p' <<<"$IWCONFIG_OUTPUT" | head -n1 | tr '[:upper:]' '[:lower:]')"
if [[ -z "$FREQ_GHZ" || -z "$TARGET_BSSID" || "$TARGET_BSSID" == "00:00:00:00:00:00" ]]; then
  echo "ERROR: $WIFI_IFACE is not associated to a Wi-Fi AP. Connect to the dedicated hotspot/AP first." >&2
  exit 2
fi
CONNECTED_CHANNEL="$(awk -v ghz="$FREQ_GHZ" 'BEGIN {
  f = ghz * 1000
  if (f >= 2400 && f < 2500) c = int((f - 2407) / 5 + 0.5)
  else if (f >= 5000 && f < 5925) c = int((f - 5000) / 5 + 0.5)
  else if (f >= 5925 && f <= 7125) c = int((f - 5950) / 5 + 0.5)
  else exit 1
  if (c > 0) print c; else exit 1
}')" || {
  echo "ERROR: could not map active Wi-Fi frequency $FREQ_GHZ GHz to a channel." >&2
  exit 2
}
if [[ -z "$CHANNEL" ]]; then CHANNEL="$CONNECTED_CHANNEL"; fi
if [[ "$CHANNEL" != "$CONNECTED_CHANNEL" ]]; then
  echo "ERROR: requested channel $CHANNEL does not match active link channel $CONNECTED_CHANNEL. Connect to the intended AP/channel first." >&2
  exit 2
fi
if (( CHANNEL < 36 )) && [[ "$LA_TRIGGER" != "manual" ]] && [[ "${WIFI_PRESENCE_ALLOW_2G:-0}" != 1 ]]; then
  echo "ERROR: qualification requires a 5 GHz AP (prefer channel 149). 2.4 GHz CRCOK/beacon frames may exceed the 389.6 us pre-trigger window and lose the L-LTF. For diagnostic-only 2.4 GHz capture, set WIFI_PRESENCE_ALLOW_2G=1." >&2
  exit 2
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
MANIFEST="$OUT_DIR/run_manifest.json"
RESTORE_NEEDED=1

source "$ROOT/tools/lib/rx_process_supervisor.sh"

cleanup() {
  local rc=$?
  trap - EXIT INT TERM
  if ! stop_rx_child; then
    rc=1
    RESTORE_NEEDED=0
    echo "CRITICAL: automatic driver restore skipped because RX did not exit. After confirming the process is gone, restore with: sudo bash '$BIND' '$BDF' --restore" >&2
  fi
  if [[ "${RESTORE_NEEDED:-0}" == 1 ]]; then
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
  target AP  : ${TARGET_BSSID:-unknown (metadata only)}
  trigger    : $LA_TRIGGER (manual is a diagnostic; it does not identify an AP frame)
  LA mode    : 20 Msps, dma0, BB debug port 0x880
  captures   : $CAPTURE_COUNT
  interval   : $CAPTURE_INTERVAL_MS ms between captures
  trigger time: ${LA_TRIGGER_TIME_US} us (Realtek MAC trigger-time register; not sample duration)
  IQ buffer  : up to 8192 complex samples; 409.6 us at 20 Msps
  output     : $OUT_DIR/capture.NNNN.bin
  CSI series : $CSI_SERIES

The adapter's normal Wi-Fi connection will be unavailable during this run.
The script does NOT restart NetworkManager or reboot the machine. It restores
rtw_8821ce before exit. Run locally at the machine's physical console.
No firmware flash, persistent binding, or system configuration change is performed.
MSG

"$PY" - "$MANIFEST" "$BDF" "$CHANNEL" "$LA_TRIGGER" "$LA_TRIGGER_TIME_US" "$CAPTURE_COUNT" "$CAPTURE_INTERVAL_MS" "${TARGET_BSSID:-}" <<'PYMANIFEST'
import json, os, sys, time
p, bdf, channel, trigger, trigger_time, count, interval, bssid = sys.argv[1:]
json.dump({
  "created_unix": time.time(), "pci_bdf": bdf, "channel": int(channel),
  "bandwidth_mhz": 20, "trigger": trigger, "trigger_time_us": int(trigger_time),
  "capture_count_requested": int(count), "capture_interval_ms_configured": int(interval),
  "connected_bssid": bssid or None, "wifi_interface": os.environ.get("WIFI_PRESENCE_INTERFACE", "wlp1s0"), "rx_metadata_enabled": True,
  "sample_rate_msps": 20, "dma": 0, "debug_port": "0x880",
  "max_samples_per_capture": 8192, "adapter": "RTL8821CE 1T1R"
}, open(p, "w"), indent=2)
PYMANIFEST

bash "$BIND" "$BDF" || exit $?

# Repeated captures happen in one rxdemo process and one VFIO ownership window.
# SIGINT is sent only after the requested successful-capture count is reached.
# A hard deadline and TERM fallback prevent a stuck RX loop from blocking driver restore.
RX_ENV=(
  DEVOURER_PCIE_BDF="$BDF"
  DEVOURER_CHANNEL="$CHANNEL"
  DEVOURER_BW=20
  DEVOURER_LOG_LEVEL=debug
  DEVOURER_RX_PRESENCE_META=1
  DEVOURER_LA_DELAY_MS=2000
  DEVOURER_LA_CAPTURE="$LA_TRIGGER/20M/dma0/port:0x880/t$LA_TRIGGER_TIME_US/all"
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
  echo "CRITICAL: RX process ignored SIGINT/SIGTERM; sending SIGKILL." >&2
  kill -KILL "$RX_PID" 2>/dev/null || true
  for ((tick=0;tick<40;tick++)); do
    rx_is_running || break
    sleep 0.25
  done
  if rx_is_running; then
    echo "CRITICAL: RX remains alive after SIGKILL; refusing to restore the PCI driver while the process may still own VFIO." >&2
    exit 1
  fi
fi
wait "$RX_PID"
RX_STATUS=$?
RX_PID=""
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
    --output "$CSI_SERIES" --min-captures 0; then
  echo "ERROR: CSI time-series extraction failed. Raw IQ files and log retained in $OUT_DIR" >&2
  exit 1
fi

echo "Capture complete. Raw IQ files: $OUT_DIR/capture.NNNN.bin"
echo "Temporal CSI series: $CSI_SERIES"
echo "Capture log: $LOG"
echo "Run manifest: $MANIFEST"
if ! "$PY" "$ROOT/tools/analyze_presence_run.py" \
    --log "$LOG" --series "$CSI_SERIES" --manifest "$MANIFEST" \
    --output-prefix "$OUT_DIR/presence_audit"; then
  echo "WARNING: capture/CSI audit did not meet the predeclared quality gates." >&2
  echo "This is not a human-presence result; inspect presence_audit.json before any sensing experiment." >&2
fi
