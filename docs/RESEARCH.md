# Research notes: device-free Wi-Fi occupancy sensing

## What the literature measures
Most device-free occupancy/counting papers use Channel State Information (CSI), the per-subcarrier complex channel response. CSI contains much richer channel information than a single received-signal-strength (RSSI) value. Human movement changes multipath propagation and therefore CSI amplitude/phase patterns. Counting stationary people is harder and requires environment-specific calibration and training data.

## Papers to start with
1. Jeong et al., "DFC: Device-free human counting through WiFi fine-grained subcarrier information", IET Communications, 2021. DOI: 10.1049/cmu2.12043. Uses CSI amplitude attenuation/variation and a learned probability model.
2. Xu et al., "Area human sensing via ambient Wi-Fi signals", IET Communications, 2021. DOI: 10.1049/cmu2.12261. Combines CSI features and SVM for people count and activity recognition.
3. "Device-free Pedestrian Count Estimation Using Wi-Fi Channel State Information", IEEE ITSC 2021. Uses ESP32 CSI and a DNN; reports up to 12 pedestrians in its evaluated setup.
4. "FreeCount: Device-Free Crowd Counting with Commodity WiFi", IEEE GLOBECOM 2017. Uses CSI extracted by upgrading router software and transfer-kernel learning.
5. Son and Park, "Channel State Information (CSI) Amplitude Coloring Scheme for Enhancing Accuracy of an Indoor Occupancy Detection System Using Wi-Fi Sensing", Applied Sciences, 2024. DOI: 10.3390/app14177850.
6. Cha, Kim and Choi, "Meta-Learning-Based People Counting and Localization Models Employing CSI from Commodity WiFi NICs", arXiv:2502.03117, 2025.

## Hardware and extraction-tool compatibility
Laptop PCI ID is 10ec:c821, Realtek RTL8821CE, using Linux driver rtw_8821ce. Established CSI extraction projects reviewed do not list RTL8821CE:
- Linux 802.11n CSI Tool: Intel 5300.
- Atheros CSI Tool: ath9k devices such as AR9580/AR9590/AR9344/QCA9558.
- Nexmon CSI: supported Broadcom/Cypress chipsets and selected devices.
- PicoScenes / FeitCSI: selected Intel AX200/AX210 and other listed hardware.
- ESP32 CSI: ESP32 family.
This project therefore does not claim CSI access on the installed adapter.

## Open-source code references
- CSIKit: https://github.com/Gi-z/CSIKit (parsing/processing CSI files from supported hardware; not a capture driver).
- Atheros CSI Tool: https://github.com/xieyaxiongfly/Atheros-CSI-Tool
- Espressif ESP-CSI: https://github.com/espressif/esp-csi
- Nexmon CSI: https://github.com/seemoo-lab/nexmon_csi
- Linux 802.11n CSI Tool: https://github.com/dhalperi/linux-80211n-csitool

## Scientific caveat and current implementation status
The original `wifi_sense` prototype reads the connected network signal percentage via NetworkManager nmcli. That value is a coarse, quantized scalar affected by access-point movement, transmit power, interference, orientation, doors, and other environmental factors. Its anomaly score is a signal-change indicator, NOT a human-presence probability and NOT a people count.

A separate userspace PCIe/VFIO path using OpenIPC Devourer has now captured raw IQ from the laptop's RTL8821CE and extracted a 52-active-subcarrier H(k) estimate from an L-LTF. Repeated sequential capture and temporal CSI JSONL extraction are implemented and software-tested; a repeated hardware dataset and its stability analysis remain pending. The RTL8821CE is 1T1R, so multi-person count accuracy must not be assumed. Do not report presence/count accuracy without held-out sessions, room-level testing, and ground-truth labels.
