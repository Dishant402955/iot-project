# Public Wi-Fi CSI Presence Dataset

## Session 1: anonymized interleaved capture

`interleaved_session_1_anonymized.jsonl` contains one completed five-round interleaved physical capture session for an experimental stationary room-presence detector.

- 5 paired rounds, 10 batches total
- 5 ABSENT batches and 5 PRESENT batches, alternating order by round
- 50 capture attempts per batch; 500 valid CSI profiles total
- 52 active subcarriers per strict CSI profile
- 500/500 strict CSI, target-attributed strict CSI, and RX-idle checks
- Wi-Fi channel 149, 20 MHz

## Anonymization

The public copy retains occupancy labels, CSI feature profiles, acquisition-quality metrics, channel configuration, and the experimental protocol. It omits the access-point BSSID, exact wall-clock timestamps, and machine-local filesystem paths. Batch timing is represented as elapsed seconds from the start of the session. Raw IQ archives are not included.

## Data format

The JSONL file contains one `session_metadata` record followed by ten `interleaved_presence_batch` records. Each batch includes the condition/label, round number, acquisition counts and fractions, summary RF metrics, and `profiles_db_centered` feature vectors.

## Important limitations

This is a single controlled-environment development/validation session, not a held-out evaluation. It must not be interpreted as evidence of generalization across rooms, devices, people, or environments. The detector remains experimental; `UNKNOWN`/insufficient-capture handling and independent held-out evaluation are required before any practical deployment.
