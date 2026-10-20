"""Analysis windows and the window-level feature table.

Windows are cut *inside* tag-defined segments (never across a boundary):
30-s windows with a 15-s step. Segments shorter than 30 s but at least
20 s long (some sprints) contribute one window covering the whole segment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.repairs import load_clean_session
from src.signals.processing import hrv_time_domain, prepare_session, window_features

WIN_S = 30.0
STEP_S = 15.0
MIN_SHORT_S = 20.0

# Physiological "state" used throughout the analysis
STATE_OF_PHASE = {
    ("STRESS", "stress"): "STRESS_TASK",
    ("STRESS", "baseline"): "SEATED_BASELINE",
    ("STRESS", "rest"): "SEATED_REST",
    ("AEROBIC", "exercise"): "AEROBIC_STAGE",
    ("AEROBIC", "warmup"): "UNLOADED_PEDALLING",
    ("AEROBIC", "cooldown"): "UNLOADED_PEDALLING",
    ("ANAEROBIC", "warmup"): "UNLOADED_PEDALLING",
    ("ANAEROBIC", "cooldown"): "UNLOADED_PEDALLING",
    ("ANAEROBIC", "sprint"): "SPRINT",
    ("AEROBIC", "recovery"): "POST_EXERCISE_REST",
    ("ANAEROBIC", "recovery"): "POST_EXERCISE_REST",
    ("ANAEROBIC", "baseline"): "PRE_EXERCISE_BASELINE",
}

# Classification target (Phase 6): the active part of each protocol
CLASS_OF_STATE = {"STRESS_TASK": "STRESS", "AEROBIC_STAGE": "AEROBIC", "SPRINT": "ANAEROBIC"}


def windows_for_segment(start: float, end: float) -> list[tuple[float, float]]:
    dur = end - start
    if dur < MIN_SHORT_S:
        return []
    if dur < WIN_S:
        return [(start, end)]
    starts = np.arange(start, end - WIN_S + 1e-9, STEP_S)
    return [(s, s + WIN_S) for s in starts]


def build_window_table(segments: pd.DataFrame, quality_cache: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (windows, segment_level) feature tables for every session."""
    win_rows, seg_rows = [], []
    for (cond, sid), g in segments.groupby(["condition", "session_id"], sort=False):
        sess, invalid = load_clean_session(cond, sid)
        p = prepare_session(sess, invalid)
        for r in g.itertuples():
            state = STATE_OF_PHASE.get((cond, r.phase))
            base = dict(condition=cond, session_id=sid, subject_id=r.subject_id, cohort=r.cohort,
                        segment=r.segment, phase=r.phase, state=state)
            # segment-level: features over the whole segment + HRV
            if r.end_s > p["duration_s"] + 1:      # segment beyond a truncation
                continue
            if r.duration_s >= MIN_SHORT_S:
                sf = window_features(p, r.start_s, r.end_s)
                sf.update(hrv_time_domain(p["ibi_t"], p["ibi"], r.start_s, r.end_s))
                seg_rows.append({**base, "start_s": r.start_s, "end_s": r.end_s,
                                 "duration_s": r.duration_s, **sf})
            for k, (s, e) in enumerate(windows_for_segment(r.start_s, r.end_s)):
                wf = window_features(p, s, e)
                win_rows.append({**base, "win_idx": k, "start_s": s, "end_s": e,
                                 "t_in_segment_s": s - r.start_s, **wf})
    return pd.DataFrame(win_rows), pd.DataFrame(seg_rows)
