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
  echo "This bootstrap currently supports x86_64 Linux (validated on Ubuntu 22.04)." >&2
  exit 2
fi
command -v apt-get >/dev/null || { echo "apt-get is required to download build dependencies." >&2; exit 1; }
command -v dpkg-deb >/dev/null || { echo "dpkg-deb is required to extract build dependencies." >&2; exit 1; }
command -v python3 >/dev/null || { echo "Python 3 is required." >&2; exit 1; }

mkdir -p "$DEB_DIR" "$EXTRACT"
PACKAGES=()
if [[ ! -x "$EXTRACT/usr/bin/cmake" || ! -f "$EXTRACT/usr/include/libusb-1.0/libusb.h" ]]; then
  PACKAGES+=(cmake cmake-data libjsoncpp25 librhash0 libusb-1.0-0-dev libusb-1.0-0)
fi
if [[ ! -x "$VENV/bin/python" || ! -f "$VENV/bin/activate" ]]; then
  PACKAGES+=(python3.10-venv python3-pip-whl python3-setuptools-whl python3-distutils python3-lib2to3 libpython3.10-stdlib)
fi

if ((${#PACKAGES[@]})); then
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  (
    cd "$TMP"
    apt-get download "${PACKAGES[@]}"
  )
  for deb in "$TMP"/*.deb; do
    dpkg-deb -x "$deb" "$EXTRACT"
    cp -f "$deb" "$DEB_DIR/"
  done
fi

# apt-get may skip a runtime package already installed on the host even when
# only its development package was downloaded. Ensure the shared object is
# present in our private prefix so the linker does not fall back to libusb.a.
if [[ ! -f "$EXTRACT/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0.3.0" ]]; then
  TMP_USB="$(mktemp -d)"
  (cd "$TMP_USB" && apt-get download libusb-1.0-0)
  for deb in "$TMP_USB"/*.deb; do
    dpkg-deb -x "$deb" "$EXTRACT"
    cp -f "$deb" "$DEB_DIR/"
  done
  rm -rf "$TMP_USB"
fi

# Debian's extracted libusb pkg-config file may embed the extraction-time
# absolute path. Make it relocatable so moving/cloning the repository works.
USB_PC="$EXTRACT/usr/lib/x86_64-linux-gnu/pkgconfig/libusb-1.0.pc"
if [[ -f "$USB_PC" ]]; then
  sed -i 's|^prefix=.*|prefix=${pcfiledir}/../../..|' "$USB_PC"
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv --without-pip "$VENV"
fi
if ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  # Use Ubuntu's locally extracted ensurepip + wheel packages without writing
  # anything into /usr. distutils comes from the extracted stdlib package.
  PYTHONPATH="$EXTRACT/usr/lib/python3.10${PYTHONPATH:+:$PYTHONPATH}" \
    "$VENV/bin/python" - <<PY
import ensurepip
ensurepip._WHEEL_PKG_DIR = "$EXTRACT/usr/share/python-wheels"
ensurepip.bootstrap(upgrade=True)
PY
fi

source "$ROOT/tools/devourer_env.sh"
"$WIFI_PRESENCE_PYTHON" -m pip install --disable-pip-version-check 'numpy==2.2.6'
cmake --version | head -n1
"$WIFI_PRESENCE_PYTHON" -c 'import numpy; print("NumPy", numpy.__version__)'
[[ -f "$DEPS/root/usr/include/libusb-1.0/libusb.h" ]]
echo "Project-local Devourer toolchain is ready. No system packages were installed."
