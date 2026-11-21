# IoT Project: Wi-Fi Presence Sensing

A Linux prototype for Wi-Fi presence-sensing research using the laptop’s built-in RTL8821CE adapter. It includes an older NetworkManager signal-strength prototype and a separately validated userspace PCIe/VFIO raw-IQ-to-CSI acquisition path.

## Target laptop
- Realtek RTL8821CE (PCI ID 10ec:c821), Linux driver rtw_8821ce
- Intel Core i3-1005G1
- Ubuntu 22.04-based system, Linux 6.8
- Connected interface observed as wlp1s0

## Important limitation
The original `wifi_sense` collector reads the connected network signal percentage from NetworkManager (nmcli), which may be based on its scan cache rather than a fresh per-packet measurement. It is not CSI and does not detect people or estimate their number. Separately, the RTL8821CE has now produced a real raw IQ capture and 52-tone H(k) estimate using Devourer PCIe/VFIO; repeated temporal acquisition is implemented but still awaits a local hardware run.

## Clone and build

```bash
git clone https://github.com/Dishant402955/iot-project.git
cd iot-project

# Build the original signal-strength prototype
cmake -S . -B build
cmake --build build -j2
ctest --test-dir build --output-on-failure

# Bootstrap an isolated toolchain and build the RTL8821CE CSI path
./tools/setup_devourer_env.sh
./tools/build_devourer_pcie.sh
```

The Devourer setup downloads and extracts its build dependencies under `vendor/.local-deps` and creates `vendor/.venv`. It does not install system packages or require sudo. The hardware capture step is separate and requires a deliberate local-console sudo action.

## Use
    ./wifi_sense inspect
    ./wifi_sense collect --label 0 --seconds 120 --output data/empty.csv
    ./wifi_sense collect --label 1 --seconds 120 --output data/one_person.csv
    ./wifi_sense monitor

Labels are ground-truth annotations: 0=empty and 1..5=observed people in the room. Keep laptop and access point fixed, collect multiple sessions per label, and note room, distance, orientation, and activity separately. Captures append to CSV files.

The monitor forms a rolling signal-strength feature window and reports a relative disturbance score. Because NetworkManager may return cached scan results, repeated readings can remain unchanged between scans. The score is not a probability, occupancy class, or count.

## Privacy
The collector reads the laptop's own connected-link radio metrics. It does not scan client devices, capture payloads, identify nearby devices, or transmit packets.

See docs/RESEARCH.md for papers, hardware compatibility notes, and open-source CSI tooling.


## CSI hardware feasibility and next path

The standard Linux `rtw88` driver does not expose receive-side per-subcarrier CSI. A separate userspace PCIe/VFIO path using [OpenIPC Devourer](vendor/devourer) has successfully captured raw IQ on this laptop (RTL8821C cut 4, 8,192 samples) and extracted 52 active-subcarrier H(k) magnitude/phase values. Repeated capture is implemented and software-tested; a time-separated hardware CSI series is the next validation run. Run `sudo bash tools/rtl8821ce_pcie_la_capture.sh` locally at the physical console; it auto-detects the current Wi-Fi channel and collects 10 time-separated captures and a combined `csi_series.jsonl`. The script temporarily takes ownership of the Wi-Fi adapter, does not restart NetworkManager, and restores the normal driver before exit. See [the staged bring-up plan](docs/RTL8821CE_DEVOURER_BRINGUP.md) and [the original driver-path investigation](docs/RTL8821CE_CSI_FEASIBILITY.md).

The existing NetworkManager signal-strength collector remains a coarse signal-disturbance prototype, not CSI and not a people counter. Do not train a CSI model on those signal percentages.
