# Model

## Selected demo model

The live demonstration uses an **ExtraTreesClassifier** trained on 40 batch-level examples: 20 `ABSENT` and 20 `PRESENT`. Each example summarizes one batch of 50 capture attempts.

The feature vector contains 104 temporal measurements: 52 per-tone median absolute deviation values followed by 52 per-tone standard deviation values. These summarize variation across the accepted measurements within a batch.

The model uses 250 trees, a maximum depth of 2, a minimum of 2 samples per leaf, square-root feature selection, balanced class weights, and a fixed random seed.

## Files

- `models/presence_temporal_extra_trees_dev_v1.joblib`: trained model weights.
- `models/presence_temporal_extra_trees_dev_v1.json`: model identity, training data provenance, configuration, evaluation references, and artifact checksum.
- `tools/train_presence_demo_model.py`: explicit retraining script. It is not run by the live demo.

The live demo checks the model checksum and identity before using the weights.
