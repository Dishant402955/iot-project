# Live Wi-Fi presence detection feasibility on the current laptop

**Host identified from DMI:** Dell Inspiron 15 3511, board 0MW5PD, Intel Core i3-1005G1 (10th generation). Current WLAN: Realtek RTL8821CE, PCI `10ec:c821`, 1T1R, driver `rtw_8821ce`.

## Current adapter

The current Devourer acquisition path is useful for low-level RF experimentation, but not a direct RF-DS source:

- External AP / bistatic reception, not monostatic self-transmission sensing.
- 20 MHz channel, 52 legacy L-LTF tones, versus the paper's 160 MHz / 512 calibrated CSI tones.
- 50/50 raw IQ capture was achieved, but only 18/50 CSI extractions passed quality checks in the latest known run.
- Approximate 130 ms per capture, below the paper's 100 Hz detection rate.
- No labelled live empty/occupied data and no validated detector.

**Decision:** do not claim a live detector on RTL8821CE. The only sensible next experiment on this adapter is a separately named bistatic motion/presence prototype after CSI quality and packet attribution improve.

## Replacement NIC investigation

| Candidate | Interface / capabilities | Fit to this laptop | Fit to research |
|---|---|---|---|
| Intel AX201 | CNVio2, 2x2, 160 MHz, Wi-Fi 6 | Dell lists it only for 11th-gen CPU configurations; this host reports i3-1005G1 (10th gen). Not confirmed. | IAX third-party tool claims AX201 CSI support, but its documented path is based on Linux 5.15 and does not prove monostatic self-sensing or compatibility with the authors' driver. |
| Intel AX210 | PCIe/USB, 2x2, 160 MHz, Wi-Fi 6E | Not listed by Dell for this model; physical M.2 size is not sufficient evidence. | IAX claims CSI support. LiveSense paper reports AX211 / BE201, not AX210. Not proven. |
| Intel AX211 | CNVio2, Wi-Fi 6E | Exact board/CPU/BIOS compatibility not established; not listed in Dell's 3511 options. | Used in the authors' 2025/2026 sensing platform. Strongest research match, but poor purchase candidate without Dell confirmation. |
| Intel BE201 | Wi-Fi 7 | Platform/BIOS compatibility not established; likely not a supported retrofit for this older machine. | Used in LiveSense; not a realistic first upgrade for this laptop. |

## Research and sources

- Dell Inspiron 15 3511 product specifications list RTL8821CE and optional AX201; AX201 option is qualified for systems with 11th-generation processors: https://www.dell.com/en-us/shop/laptops/3511/spd/inspiron-15-3511-laptop
- Dell service manual documents the removable WLAN M.2 card and two antenna connectors: https://www.dell.com/support/manuals/en-us/inspiron-15-3511-laptop/inspiron-3511-service-manual
- Intel AX201 specifications: 2x2, 160 MHz, M.2 CNVio2: https://www.intel.com/content/www/us/en/products/compare.html?productIds=189347,130293
- IAX claims CSI extraction support for AX200/201/210/211 and 20/40/80/160 MHz, but its README says the Intel CSI path is based on Linux 5.15.x and tested kernel compatibility is limited: https://github.com/fflq/iax
- LiveSense paper reports AX211 / BE201 and synchronized CSI at 40 Hz or higher: https://arxiv.org/abs/2603.06545
- RF-DS paper: https://arxiv.org/abs/2603.10845

## Recommendation

Do not buy a WLAN card yet. The current laptop is not a proven platform for the selected monostatic paper. A safe next hardware decision requires confirmation of the actual M.2 electrical interface and BIOS whitelist for this exact board/CPU, plus confirmation that the sensing driver works on the proposed card. If those cannot be established, use a dedicated supported sensing platform rather than risking the laptop's only network adapter.


## Acquisition rescue work (2026-11-21)

The strict CSI series extractor now writes a per-capture diagnostics sidecar (`csi_series.jsonl.diagnostics.json`). For failed L-LTF searches it records how many candidates failed repeated-symbol coherence, L-STF periodicity rejection, and CFO-corrected two-symbol agreement, plus the best observed quality values. This is intended to distinguish trigger/window/SNR problems from false periodic candidates. It does not relax the extraction gates. The synthetic test covers two valid captures and one noise-only capture and confirms that the noise is rejected while diagnostics are retained. See `docs/LIVE_DETECTOR_STATUS.md`.

The `rxdemo` target rebuilt successfully. CMake was configured to use `vendor/.venv/bin/python` so the two CSI CTest tests execute instead of being skipped due to system Python lacking NumPy. `la_capture_sequence`, `la_csi_math`, and `la_csi_series` all pass. A fresh physical-console capture is still required to learn why the last real run yielded only 18/50 strict CSI estimates.
