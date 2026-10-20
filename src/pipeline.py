"""Build the analysis tables from raw data (Phases 2-4).

    python -m src.pipeline

Writes data/processed/windows_raw.csv (30-s windows) and
data/processed/segments_features.csv (whole segments, incl. HRV).
Quality flags are added afterwards in src/signals/quality.py.
"""

from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src.data.empatica import list_sessions, load_session
from src.data.protocol import segment_session
from src.features.windows import build_window_table

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
INTERIM = ROOT / "data" / "interim"


def build_segments() -> pd.DataFrame:
    segs = [segment_session(load_session(r.condition, r.session_id))
            for r in list_sessions().itertuples()]
    seg = pd.concat(segs, ignore_index=True)
    seg.to_csv(INTERIM / "segments.csv", index=False)
    return seg


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    t = time.time()
    seg = build_segments()
    windows, seg_feat = build_window_table(seg)
    windows.to_csv(PROCESSED / "windows_raw.csv", index=False)
    seg_feat.to_csv(PROCESSED / "segments_features.csv", index=False)
    print(f"{len(windows)} windows, {len(seg_feat)} segments in {time.time() - t:.0f} s")


if __name__ == "__main__":
    main()
