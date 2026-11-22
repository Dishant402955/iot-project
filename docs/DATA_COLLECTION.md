# Data collection

The project team collected the data through repeated controlled experiments in the same room. Each experiment batch represented either an empty room (`ABSENT`) or a room with a stationary person (`PRESENT`). The two conditions were alternated across paired rounds and repeated over five collection sessions.

The temporal Extra Trees model uses four development sessions. They contribute **40 batches**, with **50 capture attempts per batch**:

**40 batches × 50 attempts = 2,000 capture attempts.**

Each batch is one model training example, so the model has 40 examples: 20 `ABSENT` and 20 `PRESENT`. A separate session was reserved for a previous benchmark and was not accessed when creating or selecting this temporal model.

The repository's `data/public_dataset/` directory contains anonymized copies. Original labelled collection files and raw capture archives are kept outside the public repository.
