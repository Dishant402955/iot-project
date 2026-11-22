# Current RTL8821CE versus the RF-DS paper

| Requirement | Paper | Current laptop / Devourer | Consequence |
|---|---|---|---|
| Sensing geometry | Monostatic Tx/Rx on one laptop NIC | Existing acquisition listens to external AP traffic (bistatic) | Not the same RF path |
| Bandwidth | 160 MHz | 20 MHz current capture | Nominal range resolution is 7.5 m rather than 0.94 m |
| CSI tones | 512 | 52 legacy L-LTF active tones | Different frequency sampling and range response |
| CSI rate | 10 Hz idle / 100 Hz detection | Approximately 130 ms per capture, theoretical ~7.7 captures/s before trigger waits | Cannot meet either paper rate in current acquisition path |
| RF front-end | Wi-Fi 6E / Wi-Fi 7 laptop hardware, 5.8 GHz in paper | RTL8821CE 1T1R 802.11ac | No demonstrated support for paper's monostatic CSI mode |

The existing Devourer path has demonstrated raw IQ capture and 52-tone L-LTF H(k) extraction. That is valuable groundwork, but it does not satisfy the paper's 160 MHz monostatic input requirements. Do not run VFIO capture while relying on this same Wi-Fi adapter for remote connectivity: binding it temporarily removes the normal network interface.

The immediate reproduction target is therefore the published calibrated CSI dataset. A separate live bistatic experiment may be explored later, but it must be named and evaluated as an adaptation, not as an exact reproduction of RF-DS.


## Host-specific upgrade investigation (2026-11-21)

The current host identifies as **Dell Inspiron 15 3511**, board `0MW5PD`, with the RTL8821CE at `0000:01:00.0`. Dell's published Inspiron 15 3511 specifications list the Intel AX201 as an official optional WLAN module alongside the RTL8821CE. Dell's service manual documents a removable M.2 WLAN card and Main/Aux antenna connections. Intel specifies AX201 as 2x2, 160 MHz, M.2 CNVio2. This makes AX201 a plausible hardware upgrade candidate for this exact laptop, subject to checking the actual board/antenna configuration and exact card SKU.

However, the selected HPD paper and the associated LiveSense platform report evaluation on AX211 / BE201, not AX201. AX201 is not a confirmed drop-in replacement for the paper's modified driver and monostatic sensing pipeline. Do not purchase any replacement yet. First verify the exact board-level WLAN interface and BIOS support for this CPU configuration, then ask the authors whether their driver/firmware changes support AX201 or AX210. AX210 uses PCIe/USB, unlike AX201 CNVio2, but Dell does not list AX210 as an option for this model. The LiveSense demo itself reports AX211 / BE201, not AX201 or AX210.

Sources: Dell Inspiron 15 3511 specifications and service manual; Intel AX201 product specifications; paper's stated AX211/BE201 platform. Links: https://www.dell.com/en-us/shop/laptops/3511/spd/inspiron-15-3511-laptop ; https://www.dell.com/support/manuals/en-us/inspiron-15-3511-laptop/inspiron-3511-service-manual ; https://www.intel.com/content/www/us/en/products/compare.html?productIds=189347,130293
