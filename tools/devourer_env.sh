#!/usr/bin/env bash
# Source this file to use the isolated, project-local Devourer toolchain.
_WIFI_PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_WIFI_LOCAL_DEPS="$_WIFI_PROJECT_ROOT/vendor/.local-deps"
export PATH="$_WIFI_LOCAL_DEPS/root/usr/bin:$PATH"
export LD_LIBRARY_PATH="$_WIFI_LOCAL_DEPS/root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PKG_CONFIG_PATH="$_WIFI_LOCAL_DEPS/root/usr/lib/x86_64-linux-gnu/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
export PYTHONPATH="$_WIFI_LOCAL_DEPS/root/usr/lib/python3.10${PYTHONPATH:+:$PYTHONPATH}"
export WIFI_PRESENCE_PYTHON="$_WIFI_PROJECT_ROOT/vendor/.venv/bin/python"
unset _WIFI_PROJECT_ROOT _WIFI_LOCAL_DEPS
