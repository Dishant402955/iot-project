# Vendored Devourer source and local changes

This repository is the single Git repository for the IoT project. Devourer is stored as ordinary source under `vendor/devourer`, not as a nested Git repository or submodule, so the RTL8821CE-specific changes are versioned together with the project.

## Upstream provenance

- Upstream: https://github.com/OpenIPC/devourer
- Pinned upstream commit: `19cf1450d82fabc0c430bb1a252c963ef1da16d2`
- Upstream license: GPL-2.0; the upstream `vendor/devourer/LICENSE` and notices are retained.
- The optional kernel-driver reference submodules listed in the upstream `.gitmodules` are not populated. They are not required for this project's RTL8821CE PCIe/VFIO build. Other Devourer chipset backends may require those reference trees and are outside this project's validated scope.

## Local project changes on top of the pinned source

- `examples/rx/main.cpp`: optional sequential LA re-arm, numbered output files, timestamped capture events, robust write failure reporting; default remains one-shot when count is not configured.
- `examples/rx/LaCaptureSequence.h`: bounded sequence and output-path helper.
- `tests/la_capture_sequence_selftest.cpp`: no-hardware test for sequence timing, cancellation, failure handling, and distinct filenames.
- `tests/la_csi_series_selftest.py`: synthetic end-to-end repeated-capture CSI test.
- `tools/la_csi_series.py`: combines multiple DVLA files into a time-indexed, per-tone CSI JSONL dataset.
- `CMakeLists.txt`: registers the repeated-capture and CSI-series tests.
- `tests/pcie_vfio_bind.sh`: executable bit retained for direct local invocation.

The top-level repository owns all future changes. Do not create commits inside `vendor/devourer`; work from the top-level `iot-project` repository only.
