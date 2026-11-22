# Anonymized project dataset

These five JSONL files are anonymized records from experiments collected by the project team in a controlled room setup. Each session contains repeated batches under two conditions: an empty room (`ABSENT`) and a stationary person in the room (`PRESENT`). The conditions were alternated across rounds.

Each session contains 10 batches, with 50 capture attempts per batch. Sessions 1, 2, 4 and 5 were used as development data for the temporal Extra Trees model. Session 3 was kept separate from that model's training and selection.

The model's development examples are batch-level: 40 batches × 50 capture attempts = 2,000 attempts, producing 40 examples (20 per class). The public files preserve the anonymized experiment records; they do not include the original labelled collection files or raw capture archives.
