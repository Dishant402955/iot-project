#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ ! -x "$ROOT/vendor/.local-deps/root/usr/bin/cmake" || \
      ! -x "$ROOT/vendor/.venv/bin/python" || \
      ! -f "$ROOT/vendor/.local-deps/root/usr/include/libusb-1.0/libusb.h" ]]; then
  bash "$ROOT/tools/setup_devourer_env.sh"
fi
source "$ROOT/tools/devourer_env.sh"
SRC="$ROOT/vendor/devourer"
BUILD="$SRC/build-rtl8821ce-pcie"
if [[ ! -x "$WIFI_PRESENCE_PYTHON" ]]; then
  echo "Missing project-local Python environment: $WIFI_PRESENCE_PYTHON" >&2
  exit 1
fi
cmake -S "$SRC" -B "$BUILD" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS="-I$ROOT/vendor/.local-deps/root/usr/include" \
  -DCMAKE_C_FLAGS="-I$ROOT/vendor/.local-deps/root/usr/include" \
  -DDEVOURER_PCIE=ON \
  -DDEVOURER_JAGUAR2_8821C=ON \
  -DDEVOURER_JAGUAR1=OFF \
  -DDEVOURER_8814=OFF \
  -DDEVOURER_JAGUAR2_8822B=OFF \
  -DDEVOURER_JAGUAR3_8822C=OFF \
  -DDEVOURER_JAGUAR3_8822E=OFF \
  -DDEVOURER_8733B=OFF \
  -DDEVOURER_KESTREL_8852B=OFF \
  -DDEVOURER_KESTREL_8852C=OFF \
  -DDEVOURER_MT7612U=OFF
cmake --build "$BUILD" --target pcieprobe rxdemo EnvConfigSelftest TriggerParseSelftest Dot11Selftest LaCaptureSequenceSelftest -j2
"$BUILD/EnvConfigSelftest"
"$BUILD/TriggerParseSelftest"
"$BUILD/Dot11Selftest"
"$BUILD/LaCaptureSequenceSelftest"
SITE="$($WIFI_PRESENCE_PYTHON -c 'import site; print(site.getsitepackages()[0])')"
PYTHONPATH="$SITE${PYTHONPATH:+:$PYTHONPATH}" ctest --test-dir "$BUILD" -R '^(la_csi_math|la_csi_series|la_capture_sequence)$' --output-on-failure
