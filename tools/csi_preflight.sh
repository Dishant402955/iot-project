#!/usr/bin/env bash
# Read-only CSI capability preflight for the current Linux Wi-Fi adapter.
# This script does not load modules, change interfaces, or claim CSI from RSSI.
set -u

section() { printf "\\n=== %s ===\\n" "$1"; }
section "Kernel"
uname -r
section "Wi-Fi PHY devices"
if compgen -G "/sys/class/ieee80211/phy*" >/dev/null; then
  for phy in /sys/class/ieee80211/phy*; do
    [ -e "$phy" ] || continue
    printf "%s: %s\\n" "$(basename "$phy")" "$(readlink -f "$phy")"
  done
else
  echo "No cfg80211 PHY device found"
fi
section "PCI Wi-Fi adapter"
if command -v lspci >/dev/null 2>&1; then
  lspci -nnk | grep -A4 -i -E "network controller|wireless" || true
else
  echo "lspci not installed"
fi
section "Loaded Realtek modules"
if command -v lsmod >/dev/null 2>&1; then
  lsmod | grep -E "^(rtw|rtl|cfg80211|mac80211)" || true
fi
section "CSI-related debugfs paths"
found=0
for root in /sys/kernel/debug/ieee80211 /sys/kernel/debug/rtw88 /sys/kernel/debug; do
  [ -d "$root" ] || continue
  while IFS= read -r path; do
    printf "%s\\n" "$path"
    found=1
  done < <(find "$root" -maxdepth 5 -iname *csi* -print 2>/dev/null | head -100)
done
[ "$found" -eq 1 ] || echo "No CSI-named debugfs interface found"
section "Capture utilities"
for cmd in iw tcpdump tshark; do
  if command -v "$cmd" >/dev/null 2>&1; then
    printf "%s: %s\\n" "$cmd" "$(command -v "$cmd")"
  else
    printf "%s: not installed\\n" "$cmd"
  fi
done
section "Interpretation"
echo "This is an interface inventory, not proof that CSI is available."
echo "RSSI, signal percentage, SNR, EVM and radiotap metadata are not per-subcarrier CSI."
echo "For RTL8821CE using upstream rtw88, see docs/RTL8821CE_CSI_FEASIBILITY.md."
