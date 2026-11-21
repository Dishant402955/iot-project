# RTL8821CE CSI bring-up: staged, reversible plan

**Current verdict (2026-11-21): real CSI extraction is confirmed on this laptop.** The RTL8821CE (`10ec:c821`) was temporarily bound to VFIO, Devourer identified RTL8821C cut 4 (UMC), captured 8,192 raw IQ samples, and `tools/la_csi.py` located an L-LTF and reconstructed 52 active-subcarrier H(k) magnitude/phase values. The kernel driver was restored successfully. Repeated time-separated capture is now implemented and software-tested, but still needs one controlled local hardware run.

## Safety boundaries

- No kernel replacement, DKMS install, driver blacklist, GRUB change, IOMMU boot-parameter change, firmware flash, or NetworkManager modification is part of this plan.
- The current kernel driver remains `rtw_8821ce` until a deliberate, temporary VFIO handoff.
- Binding VFIO disconnects this laptop's Wi-Fi. Do not do it over a remote session that depends on this same Wi-Fi link. Have local console access and another way to recover network access.
- Only PCI function `0000:01:00.0` is in scope. Its observed IOMMU group 11 contains only that function.
- The guarded capture wrapper restores the normal driver automatically on exit, including its error path. Only if it explicitly reports `CRITICAL: automatic restore failed`, use the manual restore command from the local console: `sudo vendor/devourer/tests/pcie_vfio_bind.sh 0000:01:00.0 --restore`.
- If restore fails, do not reboot repeatedly or change boot configuration. Inspect `lspci -nnk -s 01:00.0`, sysfs driver links, and NetworkManager first.

## Snapshot and provenance

- Project backup created before the vendor checkout: `/home/user/projects/wifi-presence-lab-backup-20261105-095856.tar.gz`.
- Devourer source: `vendor/devourer`, upstream `https://github.com/OpenIPC/devourer`.
- Pinned checkout used for this bring-up: `19cf1450d82fabc0c430bb1a252c963ef1da16d2` (2026-11-04).
- License: GPL-2.0; retain the upstream `LICENSE` and notices.
- Dependencies were initially unpacked under `vendor/.local-deps`; Python/NumPy is isolated under `vendor/.venv`. `tools/setup_devourer_env.sh` now recreates these local-only dependencies from a clean clone without installing system packages.

## Observed host facts

- Ubuntu 22.04-based host; kernel `6.8.0-138-generic`; x86_64.
- Adapter: Realtek RTL8821CE, PCI ID `10ec:c821`, subsystem `10ec:c828`, BDF `0000:01:00.0`.
- Original driver: `rtw_8821ce`; interface `wlp1s0`.
- IOMMU group 11 contains only `0000:01:00.0`.
- Current `/proc/cmdline` contains no explicit IOMMU boot parameter.
- PCI config revision `0x00` is not the internal silicon cut. The internal cut is decoded from SYS_CFG1 by the device HAL after power-on.

## Implementation and verification already completed

1. Created a compressed backup of the existing project before adding Devourer.
2. Cloned Devourer at the pinned commit above; source tree is clean.
3. Downloaded CMake 3.22.1, cmake-data, libusb development headers, and two CMake runtime dependencies into `vendor/.local-deps`. Nothing was installed system-wide.
4. Created a project-local Python 3.10 virtual environment and installed NumPy 2.2.6 there.
5. Configured a minimal release build with `DEVOURER_PCIE=ON` and only `DEVOURER_JAGUAR2_8821C=ON` for the target chipset.
6. Built `pcieprobe` and `rxdemo` successfully with GCC 11.4 / C++20.
7. Ran the LA CSI math self-test: PASS, recovered channel correlation `0.9907` (threshold >0.99).
8. The first local hardware capture confirmed PCIe transport, DMA, firmware boot, RX, RTL8821C cut 4 (UMC), and a successful 8,192-sample LA capture at 20 Msps. The one-shot `rxdemo` process continued receiving after its capture and hit the wrapper's 45-second timeout; this was a wrapper lifecycle issue, not a failed capture.
9. `tools/la_csi.py` successfully found the L-LTF (sample 2909, CFO +51.7 kHz) and emitted 52 finite H(k) magnitude/phase records. The user independently checked all 52 tones, their range, and finite/positive values.
10. The capture path now supports opt-in sequential re-arming (`DEVOURER_LA_COUNT`, `DEVOURER_LA_INTERVAL_MS`), distinct numbered DVLA files, successful-capture event timestamps, graceful SIGINT shutdown, and a combined temporal CSI JSONL extractor (`tools/la_csi_series.py`). One-shot remains the default in `rxdemo`.
11. The repeated-capture orchestration self-test and CSI math self-test both pass; `rxdemo` builds successfully. The new hardware sequence itself has not yet been run, deliberately: the adapter is the machine's only Wi-Fi device and must not be detached remotely.

Build warnings currently observed are upstream warnings about packed-member alignment and duplicate endian macro definitions. They did not prevent the targeted binaries from building. They are not warnings from a kernel module and no module was installed.

## Repeatable local build

From the project root:

```bash
./tools/build_devourer_pcie.sh
```

This builds the PCIe probe and RX demo, runs the headless C++ self-tests (including repeated-capture sequencing), and runs the CSI math test. Toolchain paths are local to this project.

## Hardware bring-up gates and status

Gates A–E below were completed successfully during the first local hardware capture on 2026-11-05. Gate F's one-shot capture and CSI extraction also passed. The repeated Gate F run is the only pending hardware validation. The sequence below is retained as an audit trail, not as a request to repeat completed destructive steps.

### Gate A: confirm local preconditions

```bash
lspci -nnk -s 01:00.0
readlink -f /sys/bus/pci/devices/0000:01:00.0/driver
for d in /sys/kernel/iommu_groups/11/devices/*; do basename "$d"; done
```

Expected: `10ec:c821`, driver `rtw_8821ce`, and only `0000:01:00.0` in group 11.

### Gate B: temporary VFIO handoff — PASSED

Run locally from the Devourer checkout, not over a connection that relies on this Wi-Fi adapter:

```bash
sudo tests/pcie_vfio_bind.sh 0000:01:00.0
lspci -nnk -s 01:00.0
ls -l /dev/vfio/11
```

Expected: driver `vfio-pci` and accessible group device. If any expectation fails, immediately run the restore command below and stop.

### Gate C: identity-only probe (no firmware download) — PASSED

```bash
sudo build-rtl8821ce-pcie/pcieprobe 0000:01:00.0 id
```

Expected: JSON event `pcie.id` with `ok:true`, chip ID `0x09`, and a plausible SYS_CFG1 value. If it fails, restore the normal driver and stop. Do not run the power stage after a failed identity stage.

### Gate D: power and silicon cut read — PASSED (cut 4, UMC)

```bash
sudo build-rtl8821ce-pcie/pcieprobe 0000:01:00.0 power
```

This performs PCIe ring setup, power-on and EFUSE read. Capture the complete log. Record the HAL-reported internal cut; do not infer it from PCI revision. The Devourer source warns that 8821C cut A lacks the LA clock bit and capture may time out. If power/EFUSE fails or the chip becomes unresponsive, restore the kernel driver and stop.

### Gate E: firmware and RX — PASSED

Only after Gate D succeeds, run the firmware stage:

```bash
sudo build-rtl8821ce-pcie/pcieprobe 0000:01:00.0 fw
```

Then test ambient beacon RX with the upstream PCIe RX smoke test, after inspecting its options and timeout behavior. Do not start LA capture until normal RX is demonstrated.

### Gate F: repeated LA capture and temporal CSI — SOFTWARE READY; HARDWARE RUN PENDING

The first one-shot capture and CSI extraction have already passed on this laptop. The sequential capture implementation and its software tests pass. To collect the still-pending time series, run the guarded wrapper locally at the physical console:

```bash
sudo bash tools/rtl8821ce_pcie_la_capture.sh
```

The channel is read from the currently connected `wlp1s0` link before VFIO binding (or can be supplied as the script argument). Defaults: 10 captures, approximately 1 second between captures, 20 Msps, `dma0`, debug port `0x880`, `crcok` trigger, and up to 8,192 samples per capture. Each successful capture is written to a distinct `capture.NNNN.bin` file. The wrapper stops `rxdemo` with SIGINT after the requested count, validates every dump, extracts H(k) for each usable L-LTF, and writes `csi_series.jsonl` with 52 tone records per capture plus capture index and timing metadata.

**Safety:** the normal Wi-Fi connection is unavailable while VFIO owns the adapter. Run this only at the machine's physical console, not through a remote session using this Wi-Fi. The wrapper does not restart NetworkManager or reboot; its cleanup restores `rtw_8821ce`. Do not launch another hardware capture while this one is active. If the sequence fails, retain its `/tmp/rtl8821ce-la.*` directory and log; do not change boot settings or drivers to recover.

Optional controls (export before invoking the wrapper):

```bash
WIFI_PRESENCE_CAPTURE_COUNT=10
WIFI_PRESENCE_CAPTURE_INTERVAL_MS=1000
WIFI_PRESENCE_CAPTURE_TIMEOUT_SEC=120
```

At least two captures must yield valid L-LTF estimates for the combined series to pass. A raw IQ capture without a detectable L-LTF is retained but is not counted as a valid CSI time-series point.

### Gate G: verify Ubuntu Wi-Fi restoration — ONE-SHOT RUN PASSED; RECHECK AFTER REPEATED RUN

The repeated-capture wrapper automatically invokes the restore path on exit. Verify afterward:

```bash
lspci -nnk -s 01:00.0
nmcli -t -f DEVICE,STATE,CONNECTION device status
```

Expected: `rtw_8821ce` bound again and Wi-Fi reconnects. Only if the wrapper prints `CRITICAL: automatic restore failed`, run `sudo tests/pcie_vfio_bind.sh 0000:01:00.0 --restore` from the local console. If Wi-Fi does not reconnect, inspect driver binding and NetworkManager before making any broader system change.

## What this does and does not establish

- A decoded H(k) capture establishes that this adapter can provide a per-tone channel estimate in a one-shot lab measurement; this was confirmed on the target laptop.
- Repeated sequential acquisition is implemented and software-tested; temporal hardware data is pending the next local capture run.
- It does not establish continuous high-rate CSI, stable long-term sensing, multi-person separability, or people-count accuracy.
- RTL8821CE is 1T1R. Temporal CSI features may support presence/motion experiments, but reliable count estimation requires a separate data-collection and validation study.
- The target laptop's internal cut 4 (UMC), end-to-end raw IQ capture, H(k) extraction, and successful restoration of `rtw_8821ce` are confirmed. Repeated capture and sensing accuracy remain open validation gates.
