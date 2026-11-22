"""Load the paper's released wide-format CSI CSV in bounded-memory chunks."""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import pandas as pd

_COL = re.compile(r"^(csi[12])-(\d+)-(real|imag)$")

def load_csi_csv(path: str | Path, chunksize: int = 32, max_frames: int | None = None):
    """Return (complex CSI [frames, tones], metadata DataFrame).

    The dataset README documents calibrated CSI and two LTF fields. We average
    csi1/csi2 per tone to obtain one complex vector per measurement frame.
    """
    path = Path(path)
    header = pd.read_csv(path, nrows=0).columns.tolist()
    found: dict[str, dict[str, dict[int, str]]] = {"csi1": {"real": {}, "imag": {}},
                                                   "csi2": {"real": {}, "imag": {}}}
    for col in header:
        m = _COL.match(col)
        if m:
            stream, idx, part = m.group(1), int(m.group(2)), m.group(3)
            found[stream][part][idx] = col
    indexes = sorted(set(found["csi1"]["real"]) & set(found["csi1"]["imag"]) &
                     set(found["csi2"]["real"]) & set(found["csi2"]["imag"]))
    if not indexes:
        raise ValueError(f"No matching csi1/csi2 real/imag columns found in {path}")
    if len(indexes) != 512:
        raise ValueError(f"Expected 512 CSI tones per dataset README; found {len(indexes)}")
    cols = [found[s][p][i] for s in ("csi1", "csi2") for p in ("real", "imag") for i in indexes]
    meta_cols = [c for c in ("event_timeStamp", "unix_timestamp", "channel", "bandwidth_MHz",
                             "measurement_time_repetition_ms", "frequency_carrier_MHz") if c in header]
    chunks = []
    metadata = []
    total = 0
    for frame in pd.read_csv(path, usecols=cols + meta_cols, chunksize=chunksize):
        n = len(frame)
        if max_frames is not None and total + n > max_frames:
            frame = frame.iloc[:max_frames-total]
            n = len(frame)
        if n == 0:
            break
        c1 = frame[[found["csi1"]["real"][i] for i in indexes]].to_numpy(dtype=np.float32)
        c1i = frame[[found["csi1"]["imag"][i] for i in indexes]].to_numpy(dtype=np.float32)
        c2 = frame[[found["csi2"]["real"][i] for i in indexes]].to_numpy(dtype=np.float32)
        c2i = frame[[found["csi2"]["imag"][i] for i in indexes]].to_numpy(dtype=np.float32)
        z1 = c1 + 1j*c1i
        z2 = c2 + 1j*c2i
        chunks.append(((z1 + z2) * 0.5).astype(np.complex64))
        metadata.append(frame[meta_cols].copy())
        total += n
        if max_frames is not None and total >= max_frames:
            break
    if not chunks:
        raise ValueError("No CSI frames loaded")
    return np.concatenate(chunks, axis=0), pd.concat(metadata, ignore_index=True)
