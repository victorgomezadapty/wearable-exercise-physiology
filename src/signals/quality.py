"""Window-level signal-quality rules (Phase 2).

Rules use *signal properties only*, never the expected physiological outcome
(excluding data because it "doesn't look physiological" would be circular).
Physiological plausibility is handled separately as a sensitivity analysis.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Calibrated in notebooks/02_signal_quality.ipynb (see that notebook for the
# distributions behind each number).
BVP_SQI_MIN = 0.40          # 5th percentile of clean seated windows (IBI coverage >= 70%)
HR_AGREEMENT_BPM = 10.0     # |Empatica HR - PPG dominant frequency|
CADENCE_TOL_BPM = 4.0       # PPG/HR this close to cadence or step rate => lock-in
PEDALLING_MOVEMENT_G = 0.02 # movement above which cadence lock-in is checked
PEDALLING_PERIODICITY = 0.25
EDA_LOW_CONTACT_MAX = 0.10  # share of samples < 0.05 uS
TEMP_EQUILIBRATION_S = 300  # skip the first 5 min of each recording
TEMP_VALID_MIN = 0.90
ACC_SATURATION_MAX = 0.05


def cadence_lock(df: pd.DataFrame) -> pd.Series:
    """True when HR (Empatica or PPG spectral) sits on the pedalling rhythm.

    The wrist oscillates once per foot-down, so the ACC dominant frequency is
    ~2x the cadence. Lock-in is checked against both the cadence (acc/2) and
    the step rate (acc) whenever rhythmic movement is present.
    """
    pedalling = (df.acc_movement > PEDALLING_MOVEMENT_G) & (df.acc_periodicity > PEDALLING_PERIODICITY)
    step = df.acc_dom_freq_per_min
    lock = pd.Series(False, index=df.index)
    for hr_col in ("hr_mean", "hr_bvp_spectral"):
        for k in (0.5, 1.0):
            lock |= (df[hr_col] - k * step).abs() <= CADENCE_TOL_BPM
    return lock & pedalling


def add_quality_flags(df: pd.DataFrame) -> pd.DataFrame:
    q = df.copy()
    q["cadence_lock"] = cadence_lock(q)
    q["hr_agreement_bpm"] = (q.hr_mean - q.hr_bvp_spectral).abs()
    q["hr_valid"] = (q.hr_mean.notna() & (q.bvp_sqi >= BVP_SQI_MIN)
                     & (q.hr_agreement_bpm <= HR_AGREEMENT_BPM) & ~q.cadence_lock)
    q["eda_valid"] = q.eda_tonic_mean.notna() & (q.eda_low_contact_frac <= EDA_LOW_CONTACT_MAX)
    q["temp_valid"] = (q.temp_valid_frac >= TEMP_VALID_MIN) & (q.start_s >= TEMP_EQUILIBRATION_S)
    q["acc_valid"] = q.acc_movement.notna() & (q.acc_saturated_frac <= ACC_SATURATION_MAX)
    q["hr_fail_reason"] = np.select(
        [q.hr_mean.isna(), q.bvp_sqi < BVP_SQI_MIN, q.cadence_lock, q.hr_agreement_bpm > HR_AGREEMENT_BPM],
        ["no HR", "low PPG quality", "cadence lock-in", "HR disagrees with PPG"], default="valid")
    return q


def masked_features(q: pd.DataFrame) -> pd.DataFrame:
    """Copy of the feature table with invalid signals set to NaN."""
    m = q.copy()
    groups = {
        "hr_valid": ["hr_mean", "hr_max", "hr_slope"],
        "eda_valid": ["eda_tonic_mean", "eda_tonic_slope", "eda_clean_sd", "eda_scr_rate", "eda_scr_amp"],
        "temp_valid": ["temp_mean", "temp_slope"],
        "acc_valid": ["acc_movement", "acc_enmo", "acc_dom_freq_per_min", "acc_periodicity"],
    }
    for flag, cols in groups.items():
        m.loc[~m[flag], cols] = np.nan
    return m
