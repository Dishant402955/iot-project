#!/usr/bin/env bash
# Prepare an isolated, user-owned toolchain for the RTL8821CE Devourer build.
# Downloads/extracts Debian packages locally; does not run apt install or sudo.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPS="$ROOT/vendor/.local-deps"
DEB_DIR="$DEPS/debs"
EXTRACT="$DEPS/root"
VENV="$ROOT/vendor/.venv"

if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo "This bootstrap currently supports x86_64 Linux (the validated target: Ubuntu 22.04)." >&2
  exit 2
fi

mkdir -p "$DEB_DIR" "$EXTRACT"
if [[ ! -x "$EXTRACT/usr/bin/cmake" || ! -f "$EXTRACT/usr/include/libusb-1.0/libusb.h" ]]; then
  command -v apt-get >/dev/null || { echo "apt-get is required to download build dependencies." >&2; exit 1; }
  command -v dpkg-deb >/dev/null || { echo "dpkg-deb is required to extract build dependencies." >&2; exit 1; }
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  (
    cd "$TMP"
    apt-get download cmake cmake-data libjsoncpp25 librhash0 libusb-1.0-0-dev
  )
  for deb in "$TMP"/*.deb; do
    dpkg-deb -x "$deb" "$EXTRACT"
    cp -f "$deb" "$DEB_DIR/"
  done
fi

# Debian's extracted libusb pkg-config file may embed the extraction-time
# absolute path. Make it relocatable so moving/cloning the repository works.
USB_PC="$EXTRACT/usr/lib/x86_64-linux-gnu/pkgconfig/libusb-1.0.pc"
if [[ -f "$USB_PC" ]]; then
  sed -i 's|^prefix=.*|prefix=${pcfiledir}/../../..|' "$USB_PC"
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check 'numpy==2.2.6'

source "$ROOT/tools/devourer_env.sh"
cmake --version | head -n1
"$WIFI_PRESENCE_PYTHON" -c 'import numpy; print("NumPy", numpy.__version__)'
[[ -f "$DEPS/root/usr/include/libusb-1.0/libusb.h" ]]
echo "Project-local Devourer toolchain is ready. No system packages were installed."
