"""Dataset inventory and first-pass signal-quality checks.

Everything here is descriptive: it reports what is in the files and flags
things that look physiologically or technically implausible. Nothing is
removed or corrected at this stage.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .empatica import (
    DOCUMENTED_FS,
    UNIFORM_SIGNALS,
    Session,
    acc_magnitude_g,
    list_sessions,
    load_session,
)

# Plausibility thresholds (first-pass, deliberately loose).
EDA_NO_CONTACT_US = 0.05      # E4 EDA this low usually means poor/no skin contact
TEMP_OFF_WRIST_C = 30.0       # wrist skin temperature below this is suspicious
HR_MIN_BPM, HR_MAX_BPM = 40, 210
IBI_MIN_S, IBI_MAX_S = 0.27, 2.0  # ~222 to 30 bpm
ACC_SATURATION_RAW = 127      # +/-2 g range in 1/64 g units -> |value| >= 127 saturates
IBI_GAP_S = 3.0               # gap between detected beats considered a dropout


def longest_constant_run(x: np.ndarray) -> int:
    """Length (samples) of the longest run of identical consecutive values."""
    if len(x) == 0:
        return 0
    change = np.flatnonzero(np.diff(x) != 0)
    edges = np.concatenate(([-1], change, [len(x) - 1]))
    return int(np.diff(edges).max())


def find_internal_repeat(x: np.ndarray, probe: int = 400, min_start: int = 1000) -> int | None:
    """Return the sample index where the first ``probe`` samples of ``x``
    re-appear verbatim (evidence of a duplicated export), else None."""
    x = np.asarray(x)
    if len(x) < min_start + probe:
        return None
    head = x[:probe]
    candidates = np.flatnonzero(x[min_start:] == head[0]) + min_start
    for c in candidates:
        if c + probe <= len(x) and np.array_equal(x[c:c + probe], head):
            return int(c)
    return None


def signal_quality_row(session: Session, name: str) -> dict:
    sig = session.signals.get(name)
    row = {"condition": session.condition, "session_id": session.session_id,
           "subject_id": session.subject_id, "signal": name}
    if sig is None:
        row["present"] = False
        return row
    df = sig.data
    first_col = df.columns[0]
    v = df[first_col].to_numpy()
    row.update(
        present=True,
        start_utc=sig.start,
        fs_header=sig.fs,
        fs_documented=DOCUMENTED_FS.get(name),
        fs_matches_doc=bool(np.isclose(sig.fs, DOCUMENTED_FS.get(name, np.nan))),
        n_samples=sig.n_samples,
        duration_min=sig.duration_s / 60,
        n_nan=int(df.isna().sum().sum()),
        longest_flat_s=longest_constant_run(v) / sig.fs,
        repeat_at_sample=find_internal_repeat(v, probe=max(int(30 * sig.fs), 40),
                                              min_start=int(60 * sig.fs)),
    )
    if name == "ACC":
        mag = acc_magnitude_g(df)
        row.update(
            min=float(df.min().min()), max=float(df.max().max()),
            median=float(mag.median()),
            mag_p95_g=float(mag.quantile(0.95)),
            pct_saturated=float((df.abs() >= ACC_SATURATION_RAW).any(axis=1).mean() * 100),
        )
    else:
        row.update(min=float(np.nanmin(v)), max=float(np.nanmax(v)),
                   median=float(np.nanmedian(v)))
    if name == "EDA":
        row["pct_eda_below_0.05uS"] = float((v < EDA_NO_CONTACT_US).mean() * 100)
    if name == "TEMP":
        row["pct_temp_below_30C"] = float((v < TEMP_OFF_WRIST_C).mean() * 100)
    if name == "HR":
        row["pct_hr_out_of_range"] = float(((v < HR_MIN_BPM) | (v > HR_MAX_BPM)).mean() * 100)
    if name == "BVP":
        row["pct_bvp_exact_zero"] = float((v == 0).mean() * 100)
        row["bvp_abs_p99"] = float(np.nanpercentile(np.abs(v), 99))
    return row


def ibi_quality_row(session: Session) -> dict:
    row = {"condition": session.condition, "session_id": session.session_id,
           "subject_id": session.subject_id}
    ref = session.signals.get("BVP")
    rec_s = ref.duration_s if ref is not None else np.nan
    if session.ibi is None or session.ibi.empty:
        row.update(ibi_present=False, n_ibi=0, ibi_coverage_pct=0.0, recording_min=rec_s / 60)
        return row
    ibi = session.ibi
    t, d = ibi["t_s"].to_numpy(), ibi["ibi_s"].to_numpy()
    # Beat-to-beat gap: time between consecutive detections that is not
    # explained by the IBI itself means beats were rejected by Empatica.
    gaps = np.diff(t) - d[1:]
    succ = np.abs(np.diff(d)) / d[:-1]
    resolution = np.unique(np.round(d * 64, 6) % 1)
    row.update(
        ibi_present=True,
        ibi_start_utc=session.ibi_start,
        n_non_numeric_rows=ibi.attrs.get("n_non_numeric_rows", 0),
        t_monotonic=bool(np.all(np.diff(t) > 0)),
        n_ibi=len(ibi),
        recording_min=rec_s / 60,
        ibi_coverage_pct=float(d.sum() / rec_s * 100) if rec_s else np.nan,
        first_ibi_t_s=float(t[0]),
        last_ibi_t_s=float(t[-1]),
        n_gaps_gt3s=int((gaps > IBI_GAP_S).sum()),
        longest_gap_s=float(gaps.max()) if len(gaps) else np.nan,
        median_ibi_s=float(np.median(d)),
        pct_ibi_out_of_range=float(((d < IBI_MIN_S) | (d > IBI_MAX_S)).mean() * 100),
        pct_succ_change_gt20=float((succ > 0.2).mean() * 100) if len(succ) else np.nan,
        ibi_multiple_of_1_64s=bool(np.allclose(resolution, 0, atol=1e-3) |
                                   np.allclose(resolution, 1, atol=1e-3)),
    )
    return row


def tags_row(session: Session) -> dict:
    ref = session.signals.get("EDA") or next(iter(session.signals.values()), None)
    tags = session.tags if session.tags is not None else pd.Series([], dtype="datetime64[ns, UTC]")
    row = {"condition": session.condition, "session_id": session.session_id,
           "subject_id": session.subject_id, "n_tags": len(tags)}
    if ref is None or len(tags) == 0:
        return row
    rel = (tags - ref.start).dt.total_seconds().to_numpy()
    intervals = np.diff(rel)
    row.update(
        first_tag_s=float(rel[0]),
        last_tag_s=float(rel[-1]),
        recording_s=float(ref.duration_s),
        tags_outside_recording=int(((rel < 0) | (rel > ref.duration_s)).sum()),
        tagged_span_min=float((rel[-1] - rel[0]) / 60),
        min_tag_interval_s=float(intervals.min()) if len(intervals) else np.nan,
        tag_intervals_s=",".join(str(int(round(i))) for i in intervals),
    )
    return row


def sync_row(session: Session) -> dict:
    """Start/end alignment between signals of one session."""
    row = {"condition": session.condition, "session_id": session.session_id,
           "subject_id": session.subject_id}
    if not session.signals:
        return row
    starts = {k: s.start for k, s in session.signals.items()}
    ends = {k: s.end for k, s in session.signals.items()}
    ref = starts.get("EDA", min(starts.values()))
    for k in UNIFORM_SIGNALS:
        if k in starts:
            row[f"{k}_start_offset_s"] = (starts[k] - ref).total_seconds()
            row[f"{k}_end_offset_s"] = (ends[k] - ends.get("EDA", ends[k])).total_seconds()
    if session.ibi_start is not None:
        row["IBI_start_offset_s"] = (session.ibi_start - ref).total_seconds()
    raw = [k for k in ("ACC", "BVP", "EDA", "TEMP") if k in ends]
    row["max_raw_end_spread_s"] = (max(ends[k] for k in raw) - min(ends[k] for k in raw)).total_seconds()
    return row


def build_inventory():
    """Load every session once and return the four inventory tables."""
    sessions = list_sessions()
    q, ibi, tags, sync = [], [], [], []
    for _, r in sessions.iterrows():
        s = load_session(r.condition, r.session_id)
        q += [signal_quality_row(s, n) for n in UNIFORM_SIGNALS]
        ibi.append(ibi_quality_row(s))
        tags.append(tags_row(s))
        sync.append(sync_row(s))
    return (sessions, pd.DataFrame(q), pd.DataFrame(ibi), pd.DataFrame(tags), pd.DataFrame(sync))
