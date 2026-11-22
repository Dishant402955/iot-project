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

## Session 2: anonymized interleaved capture

`interleaved_session_2_anonymized.jsonl` contains a second completed five-round interleaved physical capture session.

- 5 paired rounds, 10 batches total
- 5 ABSENT batches and 5 PRESENT batches, alternating order by round
- 500 capture attempts; 499 valid strict CSI profiles (99.8%)
- 499/500 target-attributed strict CSI profiles (99.8%)
- RX-idle barrier: 500/500 (100%)
- All 10 batches passed both acquisition gates
- 52 active subcarriers per retained strict CSI profile
- Wi-Fi channel 149, 20 MHz

One PRESENT batch (round 3) yielded 49/50 strict CSI profiles; it still passed the configured batch acquisition gates. The dataset retains this measured shortfall rather than fabricating a 500th valid profile.

The public copy retains occupancy labels, CSI feature profiles, acquisition-quality metrics, channel configuration, and the experimental protocol. It omits the access-point BSSID, exact wall-clock timestamps, and machine-local filesystem paths. Batch timing is represented as elapsed seconds from the start of the session. Raw IQ archives are not included.

This remains controlled-environment development/validation data, not held-out evaluation or evidence of generalization across rooms, devices, people, or environments.

## Session 3: anonymized held-out interleaved capture

`interleaved_session_3_anonymized.jsonl` contains the third completed five-round interleaved physical capture session. It is designated as the untouched held-out evaluation session.

- 5 paired rounds, 10 batches total
- 5 ABSENT batches and 5 PRESENT batches, alternating order by round
- 500 capture attempts; 497 valid strict CSI profiles (99.4%)
- 497/500 target-attributed strict CSI profiles (99.4%)
- RX-idle barrier: 500/500 (100%)
- All 10 batches passed both configured acquisition gates
- 52 active subcarriers per retained strict CSI profile
- Wi-Fi channel 149, 20 MHz

Three batches yielded 49/50 valid strict CSI profiles: PRESENT rounds 3 and 4, and ABSENT round 5. These shortfalls are retained as measured. No samples were fabricated or imputed.

The public copy retains occupancy labels, CSI feature profiles, acquisition-quality metrics, channel configuration, and the experimental protocol. It omits the access-point BSSID, exact wall-clock timestamps, and machine-local filesystem paths. Batch timing is represented as elapsed seconds from the start of the session. Raw IQ archives are not included.

**Evaluation hygiene:** this session must not be used for feature selection, threshold tuning, model selection, or other development decisions. Freeze the detector using Sessions 1 and 2 first, then evaluate once on Session 3. This is one controlled room/device setup and does not establish generalization to other environments.


## Session 4: anonymized interleaved development capture

`interleaved_session_4_anonymized.jsonl` contains a fourth completed five-round interleaved physical capture session. It is development data and is not a held-out evaluation.

- 5 paired rounds, 10 batches total
- 5 ABSENT batches and 5 PRESENT batches, alternating order by round
- 500 capture attempts; 498 valid strict CSI profiles (99.6%)
- ABSENT: 248/250 valid strict CSI profiles; PRESENT: 250/250
- 498/500 target-attributed strict CSI profiles (99.6%)
- RX-idle barrier: 500/500 (100%)
- All 10 batches passed both configured acquisition gates
- 52 active subcarriers per retained strict CSI profile
- Wi-Fi channel 149, 20 MHz

Two ABSENT batches (rounds 1 and 5) yielded 49/50 strict CSI profiles each; both still passed the configured acquisition gates. The shortfalls are retained as measured; no samples were fabricated or imputed.

The public copy retains occupancy labels, CSI feature profiles, acquisition-quality metrics, channel configuration, and the experimental protocol. It omits the access-point BSSID, exact wall-clock timestamps, and machine-local filesystem paths. Batch timing is represented as elapsed seconds from the start of the session. Raw IQ archives and original labelled JSONL are not included.

Session 4 joins Sessions 1 and 2 as development data. Session 3 remains reserved as the already-consumed one-time held-out evaluation and must not be used for feature selection, threshold tuning, model selection, or other development decisions. Session 4's descriptive ABSENT/PRESENT profile distance is not a detector-accuracy measurement and must not be treated as one.


## Session 5: anonymized interleaved development capture

`interleaved_session_5_anonymized.jsonl` contains a fifth completed five-round interleaved physical capture session. It is development data, not held-out evaluation.

- 5 paired rounds, 10 batches total
- 5 ABSENT batches and 5 PRESENT batches, alternating order by round
- 500 capture attempts
- 498/500 strict structural CSI profiles (99.6%)
- 492/500 target-attributed strict CSI profiles retained (98.4%): 246 ABSENT and 246 PRESENT
- 494/500 post-arm target-source matches (98.8%)
- RX-idle barrier: 500/500 (100%)
- All 10 batches passed both configured acquisition gates
- 52 active subcarriers per retained strict CSI profile
- Wi-Fi channel 149, 20 MHz

Six attempts had strict structural CSI but did not meet the target-attribution requirement for inclusion as labelled feature profiles. The shortfalls in retained profiles occurred in PRESENT rounds 1, 4 and 5 and ABSENT rounds 2 and 3. All batches still passed the configured acquisition gates. These measured shortfalls are retained; no profiles were fabricated or imputed.

The public copy retains occupancy labels, CSI feature profiles, acquisition-quality metrics, channel configuration, and the experimental protocol. It omits the access-point BSSID, exact wall-clock timestamps, and machine-local filesystem paths. Batch timing is represented as elapsed seconds from the start of the session. Raw IQ archives and original labelled JSONL are not included.

Session 5 joins Sessions 1, 2 and 4 as development data. Session 3 remains reserved as the already-consumed one-time held-out evaluation and must not be used for feature selection, threshold tuning, model selection, or other development decisions. Session 5's descriptive ABSENT/PRESENT profile distance is not a detector-accuracy measurement and must not be treated as one.
