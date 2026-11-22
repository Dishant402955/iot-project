# L-LTF alignment recovery: 2026-11-22

## Summary

The strict CSI yield problem in the three 50-capture detector runs was caused by a candidate-alignment bug in `vendor/devourer/tools/la_csi.py`, not by quality thresholds that were too strict.

The extractor matched a single 64-sample L-LTF reference symbol and selected one `argmax`. Since the two L-LTF symbols are identical, the matched filter can peak on either symbol. If it selected the second symbol, the extractor then compared that symbol with the following SIGNAL field and rejected a valid L-LTF pair. The fallback search also discarded peaks less than 128 samples apart, which could suppress the correct first-symbol alignment when the two peaks were 64 samples apart.

## Fix

For each matched-filter peak, the extractor now tests candidate pair starts at `peak - 64`, `peak`, and `peak + 64`. The same alignment alternatives are tested in the fallback path, and nearby peaks are not collapsed before those alternatives are checked.

All original CSI gates remain unchanged:

- Exactly 52 finite active tones.
- Repeated L-LTF correlation >= 0.85.
- STF16 correlation <= 0.50.
- CFO-corrected L-LTF symbol relative error <= 0.25.
- Target-source audit match remains required by the presence collector/detector.

## Offline replay result

The three most recent 50-capture runs were reprocessed from their original raw DVLA IQ files:

| Run | Previous parser | Corrected parser |
|---|---:|---:|
| `rtl8821ce-la.aFwtHx` | 15/50 | 50/50 |
| `rtl8821ce-la.ePC9n6` | 17/50 | 50/50 |
| `rtl8821ce-la.f0AtiP` | 17/50 | 50/50 |
| **Total** | **49/150 (32.7%)** | **150/150 (100%)** |

The corrected replay was run through `la_csi_series.py`, producing 7,800 tone rows and a diagnostics file at `/tmp/rtl8821ce-three-runs-fixed-csi.jsonl.diagnostics.json`. The corresponding audit CSVs also show 150/150 RX-idle barriers and 150/150 target-source heuristic matches. Re-running the new archive reprocessor directly against all three run directories independently returned 50/50 target-attributed strict CSI for each run.

Across the recovered candidates, repeated-symbol correlation remained approximately 0.995-0.999, STF16 correlation approximately 0.048-0.079, and symbol relative error approximately 0.020-0.035. No quality threshold was relaxed.

A regression self-test now creates an L-LTF where the second symbol has a slightly stronger matched-filter peak than the first. The extractor must still return the first-symbol pair alignment and pass all three strict gates. The synthetic noise-rejection test remains in place.

## Interpretation and limits

This establishes that the 150 previously recorded IQ buffers contain recoverable strict-quality L-LTFs with the corrected alignment search. It does not establish 100% live acquisition yield under future conditions, and it does not establish human-presence classification accuracy. The three runs are acquisition-only and do not carry verified ABSENT/PRESENT labels.

The five-round interleaved occupancy dataset was captured using the previous extractor. Its raw capture directories are root-owned and not readable by the normal user account. Reprocessing those labelled raw captures with the corrected extractor is the next offline step once the user grants read access. The existing baseline must remain unchanged.

## Validation performed

- `vendor/.venv/bin/python vendor/devourer/tools/la_csi.py --selftest`: PASS, including noise rejection and repeated-symbol alignment regression.
- `vendor/.venv/bin/python vendor/devourer/tests/la_csi_series_selftest.py`: PASS.
- Replayed all 150 raw captures with the corrected extractor: 150/150 strict CSI accepted.
- Rechecked all three audit CSVs: RX-idle 150/150 and AP-source heuristic match 150/150.
- Synthetic false-positive stress check: 0/100 noise-only buffers and 0/100 16-sample-periodic interference buffers were promoted to CSI.
- No hardware capture was initiated during this fix.
