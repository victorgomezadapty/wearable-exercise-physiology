"""Event-locked physiological profiles (Phase 3).

Traces are binned (5 s), baseline-corrected to the pre-event period, averaged
within participant first (all events of that participant), and only then
summarised across participants (mean and 95% t-interval), so that each
person counts once.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from src.data.repairs import load_clean_session
from src.signals.processing import prepare_session

BIN_S = 5.0


def _hr_validity_per_second(win: pd.DataFrame, t: np.ndarray) -> np.ndarray:
    """Validity of each HR sample = validity of the nearest 30-s window centre."""
    if win.empty:
        return np.zeros(len(t), bool)
    centres = ((win.start_s + win.end_s) / 2).to_numpy()
    valid = win.hr_valid.to_numpy()
    order = np.argsort(centres)
    centres, valid = centres[order], valid[order]
    idx = np.clip(np.searchsorted(centres, t), 1, len(centres) - 1)
    left_closer = np.abs(t - centres[idx - 1]) <= np.abs(t - centres[idx])
    nearest = np.where(left_closer, idx - 1, idx)
    near_enough = np.abs(centres[nearest] - t) <= 20
    return valid[nearest] & near_enough


def event_traces(events: pd.DataFrame, windows_q: pd.DataFrame, pre_s=60.0, post_s=240.0) -> pd.DataFrame:
    """Binned traces around each event.

    events    : rows with condition, session_id, subject_id, cohort, event, onset_s
    windows_q : window table with quality flags (for HR validity)
    Returns long table: subject_id, event, signal, t_bin, value (baseline-corrected) and raw value.
    """
    bins = np.arange(-pre_s, post_s + BIN_S, BIN_S)
    rows = []
    for (cond, sid), ev in events.groupby(["condition", "session_id"]):
        sess, invalid = load_clean_session(cond, sid)
        p = prepare_session(sess, invalid)
        win = windows_q[(windows_q.condition == cond) & (windows_q.session_id == sid)]
        hr_ok = _hr_validity_per_second(win, p["hr_t"])
        mv = pd.Series(p["acc_mag"]).rolling(32, center=True, min_periods=16).std().to_numpy()
        series = {
            "HR": (p["hr_t"], np.where(hr_ok, p["hr"], np.nan)),
            "HR_unfiltered": (p["hr_t"], p["hr"]),
            "EDA": (p["eda_t"], p["eda"]["clean"].to_numpy()),
            "TEMP": (p["temp_t"], p["temp"]),
            "Movement": (np.arange(len(mv)) / 32.0, mv if "ACC" not in invalid else np.full(len(mv), np.nan)),
        }
        for e in ev.itertuples():
            for name, (t, y) in series.items():
                rel = t - e.onset_s
                m = (rel >= -pre_s) & (rel < post_s + BIN_S)
                if not m.any():
                    continue
                b = np.digitize(rel[m], bins) - 1
                binned = pd.Series(y[m]).groupby(b).mean()
                centre = bins[binned.index.to_numpy()] + BIN_S / 2
                vals = binned.to_numpy()
                base = np.nanmean(vals[centre < 0]) if np.isfinite(vals[centre < 0]).any() else np.nan
                for c, v in zip(centre, vals):
                    rows.append((e.subject_id, e.cohort, e.event, name, c, v, v - base))
    return pd.DataFrame(rows, columns=["subject_id", "cohort", "event", "signal", "t", "value", "delta"])


def summarise(traces: pd.DataFrame, value: str = "delta", min_subjects: int = 5) -> pd.DataFrame:
    """Participant-first average, then mean +/- 95% CI across participants."""
    per_subject = traces.groupby(["signal", "subject_id", "t"])[value].mean().reset_index()

    def ci(x):
        x = x.dropna()
        n = len(x)
        if n < min_subjects:
            return pd.Series(dict(mean=np.nan, low=np.nan, high=np.nan, n=n))
        m, se = x.mean(), x.std(ddof=1) / np.sqrt(n)
        h = se * stats.t.ppf(0.975, n - 1)
        return pd.Series(dict(mean=m, low=m - h, high=m + h, n=n))

    return per_subject.groupby(["signal", "t"])[value].apply(ci).unstack().reset_index()
