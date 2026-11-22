#!/usr/bin/env bash
# Bounded child shutdown. Caller owns RX_PID and must restore hardware only
# after this function confirms that the child is no longer running.
stop_rx_child() {
  [[ -n "${RX_PID:-}" ]] || return 0
  local state i
  state="$(ps -o stat= -p "$RX_PID" 2>/dev/null | tr -d ' ')"
  if [[ -n "$state" && "$state" != Z* ]]; then
    echo "[cleanup] Asking RX process $RX_PID to stop..." >&2
    kill -INT "$RX_PID" 2>/dev/null || true
    for ((i=0; i<${RX_STOP_INT_TICKS:-40}; i++)); do
      state="$(ps -o stat= -p "$RX_PID" 2>/dev/null | tr -d ' ')"
      [[ -z "$state" || "$state" == Z* ]] && break
      sleep 0.25
    done
    if [[ -n "$state" && "$state" != Z* ]]; then
      echo "[cleanup] RX did not stop on SIGINT; sending SIGTERM..." >&2
      kill -TERM "$RX_PID" 2>/dev/null || true
      for ((i=0; i<${RX_STOP_TERM_TICKS:-20}; i++)); do
        state="$(ps -o stat= -p "$RX_PID" 2>/dev/null | tr -d ' ')"
        [[ -z "$state" || "$state" == Z* ]] && break
        sleep 0.25
      done
    fi
    if [[ -n "$state" && "$state" != Z* ]]; then
      echo "[cleanup] RX ignored SIGINT/SIGTERM; sending SIGKILL..." >&2
      kill -KILL "$RX_PID" 2>/dev/null || true
      for ((i=0; i<${RX_STOP_KILL_TICKS:-40}; i++)); do
        state="$(ps -o stat= -p "$RX_PID" 2>/dev/null | tr -d ' ')"
        [[ -z "$state" || "$state" == Z* ]] && break
        sleep 0.25
      done
    fi
  fi
  state="$(ps -o stat= -p "$RX_PID" 2>/dev/null | tr -d ' ')"
  if [[ -n "$state" && "$state" != Z* ]]; then
    echo "CRITICAL: RX process $RX_PID is still alive after SIGKILL; refusing to rebind the PCI device while it may still own VFIO." >&2
    return 1
  fi
  wait "$RX_PID" 2>/dev/null || true
  RX_PID=""
  return 0
}
