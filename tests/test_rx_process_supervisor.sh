#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/lib/rx_process_supervisor.sh"

# Graceful child: SIGINT must stop and reap it.
bash -c 'trap "exit 130" INT; while :; do sleep 0.05; done' &
RX_PID=$!
P=$RX_PID
stop_rx_child
if kill -0 "$P" 2>/dev/null; then echo "FAIL: graceful child survived" >&2; exit 1; fi
[[ -z "$RX_PID" ]] || { echo "FAIL: RX_PID not cleared" >&2; exit 1; }

# Hostile child: ignores INT/TERM and must be KILLed, then reaped.
RX_STOP_INT_TICKS=2 RX_STOP_TERM_TICKS=2 RX_STOP_KILL_TICKS=20
bash -c 'trap "" INT TERM; while :; do sleep 0.05; done' &
RX_PID=$!
P=$RX_PID
if ! stop_rx_child; then echo "FAIL: forced child could not be reaped" >&2; exit 1; fi
if kill -0 "$P" 2>/dev/null; then echo "FAIL: forced child survived" >&2; exit 1; fi
[[ -z "$RX_PID" ]] || { echo "FAIL: RX_PID not cleared after KILL" >&2; exit 1; }
echo "RX_PROCESS_SUPERVISOR_PASS"
