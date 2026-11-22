# Live demo

From the repository root, run:

```bash
./tools/presence_demo.sh
```

Available modes:

```bash
./tools/presence_demo.sh once  # capture one batch and exit
./tools/presence_demo.sh step  # pause after each batch
```

The default mode continuously captures batches and predicts `PRESENT` or `ABSENT`. Each batch contains 50 capture attempts. The included temporal Extra Trees weights are loaded directly; launching the demo does not retrain the model.

Run the demo at the laptop's physical console. Each capture batch briefly interrupts the laptop's Wi-Fi connection. Do not run it over SSH or through a remote coding session. Press `Ctrl+C` to stop.

The prediction is an experimental result from this controlled project setup. It should not be treated as a general-purpose occupancy guarantee.
