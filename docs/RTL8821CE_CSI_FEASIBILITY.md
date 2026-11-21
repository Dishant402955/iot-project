> **Superseding update (2026-11-21):** The limitation below applies to the standard Linux `rtw88` driver path only. On this laptop, OpenIPC Devourer over PCIe/VFIO successfully captured 8,192 raw IQ samples from RTL8821CE cut 4 (UMC); `tools/la_csi.py` then extracted 52 active-subcarrier H(k) magnitude/phase estimates from an L-LTF. The normal `rtw_8821ce` driver was restored. Sequential repeated capture is implemented and software-tested, but its temporal hardware dataset is not yet collected. See [the staged bring-up plan](RTL8821CE_DEVOURER_BRINGUP.md).

# RTL8821CE CSI feasibility investigation

**Result for the standard `rtw88` driver: receive-side per-subcarrier CSI is not exposed.** A separate userspace PCIe/VFIO LA-mode path has since demonstrated real raw IQ capture and offline per-tone CSI extraction on this laptop. This does not make CSI available through `rtw88`; it is a distinct, temporary hardware-ownership path.

## Hardware and software observed

- PCI device: Realtek RTL8821CE, vendor/device `10ec:c821` (subsystem `10ec:c828`).
- Kernel: `6.8.0-138-generic`.
- Bound driver: `rtw_8821ce` (`rtw88` family).
- PHY device: `phy0`.
- The laptop exposes one Wi-Fi PHY through `/sys/class/ieee80211`.
- Kernel headers for the running kernel are installed.
- No CSI-named debugfs interface was found under `/sys/kernel/debug` during the investigation.

## Driver-source findings

The upstream `rtw88` source was inspected locally. Relevant implementation details:

1. `rtw8821c_hw_spec` sets `.csi_buf_pg_num = 0`. The MAC driver uses this field when reserving pages for CSI report buffers (`mac.c`, `rtw8821c.c`). For this chipset, the upstream driver reserves zero such pages.
2. The RTL8821C receive PHY-status parser (`query_phy_status_page0`, `query_phy_status_page1`) decodes receive power/RSSI and bandwidth-related information. It does not decode or export a per-subcarrier complex channel matrix.
3. The generic RX path passes a fixed-size PHY status metadata block to the chip-specific parser. This is PHY metadata, not a vector of per-subcarrier channel estimates.
4. CSI-related code in the chip operations includes beamforming CSI-rate/report configuration. This is associated with beamforming report handling and is not evidence that the adapter exports receive-side CSI for arbitrary ambient packets.

Upstream references:

- Linux `rtw8821c.c`: https://github.com/torvalds/linux/blob/master/drivers/net/wireless/realtek/rtw88/rtw8821c.c
- Linux `rx.c`: https://github.com/torvalds/linux/blob/master/drivers/net/wireless/realtek/rtw88/rx.c
- Linux `mac.h`: https://github.com/torvalds/linux/blob/master/drivers/net/wireless/realtek/rtw88/mac.h
- Linux `mac.c`: https://github.com/torvalds/linux/blob/master/drivers/net/wireless/realtek/rtw88/mac.c

## Why a custom userspace program cannot solve this

A userspace collector can only read data exported by the driver or another kernel interface. The current path exposes ordinary packet data and summary PHY measurements, not the per-subcarrier channel estimates required for CSI sensing. A monitor-mode capture or a more frequent RSSI poll does not create missing CSI values.

Changing `.csi_buf_pg_num` from zero is not a justified patch: it only changes a memory/page reservation parameter. It does not establish that the RTL8821C firmware/PHY generates the desired receive CSI report, define its binary layout, or add a working receive-report path. Doing this blindly risks destabilizing Wi-Fi without producing CSI. No such patch was applied and no kernel module was replaced.

## What would count as real CSI

A valid capture should contain packet-timestamped channel estimates indexed by subcarrier and receive/transmit antenna, typically complex values (I/Q or amplitude/phase) with documented scaling and packet metadata. RSSI, signal percentage, SNR, EVM, CFO, and raw PHY status metadata are not substitutes.

## Reproducible local preflight

From the project root:

```bash
./tools/csi_preflight.sh
```

The script is read-only. It inventories the current PHY, PCI adapter, loaded modules, CSI-named debugfs paths, and capture utilities. It does not claim CSI support merely because monitor mode or PHY metadata exists.

## Conclusion and next technical decision

Under the constraint **laptop hardware only**, the built-in RTL8821CE can provide one-shot per-tone CSI through Devourer's PCIe/VFIO LA-mode route. The first raw IQ capture and H(k) extraction are confirmed. The repeated-capture implementation is software-tested. The next task is running it once on hardware, then validating temporal stability before attempting presence classification. The existing NetworkManager percentage collector remains separate and must not be labeled CSI.
