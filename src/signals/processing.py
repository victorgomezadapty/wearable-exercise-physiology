"""Signal-specific processing (Phase 2).

Each signal gets its own treatment; nothing is applied blindly to all of them.

* EDA (4 Hz): spike-robust smoothing, tonic/phasic split, SCR detection with
  an *absolute* amplitude threshold (relative thresholds would make stress and
  exercise incomparable because exercise EDA is ~10x larger).
* TEMP (4 Hz): fault codes (>45 C) masked; nothing else.
* BVP (64 Hz): no waveform cleaning is attempted; only spectral descriptors
  used for quality assessment.
* ACC (32 Hz): magnitude in g; movement = dynamic component.
* HR (1 Hz, Empatica): used as delivered, gated by a quality rule.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, find_peaks, medfilt, welch

from src.data.empatica import Session, acc_magnitude_g

TEMP_FAULT_C = 45.0
SCR_MIN_AMPLITUDE_US = 0.05      # absolute floor; E4 EDA resolution is ~0.001 uS
SCR_MIN_RELATIVE = 0.02          # ...and at least 2% of the local tonic level
CARDIAC_BAND_HZ = (0.7, 3.5)     # 42-210 bpm


# --------------------------------------------------------------------------
# EDA
# --------------------------------------------------------------------------

def eda_components(eda: np.ndarray, fs: float = 4.0) -> pd.DataFrame:
    """Return clean, tonic and phasic EDA for a whole recording.

    clean  : 5-sample median filter (removes single-sample spikes) + 1 Hz low-pass
    tonic  : 0.05 Hz low-pass of clean (skin-conductance level)
    phasic : clean - tonic (skin-conductance responses)
    """
    x = np.asarray(eda, dtype=float)
    x = medfilt(x, 5)
    b, a = butter(2, 1.0 / (fs / 2), "low")
    clean = filtfilt(b, a, x)
    b, a = butter(2, 0.05 / (fs / 2), "low")
    tonic = filtfilt(b, a, clean)
    return pd.DataFrame({"clean": clean, "tonic": tonic, "phasic": clean - tonic})


def scr_peaks(clean: np.ndarray, tonic: np.ndarray, fs: float = 4.0) -> tuple[np.ndarray, np.ndarray]:
    """SCR peaks on the cleaned signal. A peak must rise above its onset by
    at least max(0.05 uS, 2% of the tonic level) within a 10-s window and be
    >= 1 s from the previous peak. The relative term stops slow sweat-level
    fluctuations at 20-50 uS (exercise) from being counted as SCRs, while the
    absolute floor applies at the low levels typical of seated stress.
    Returns (peak_indices, amplitudes)."""
    idx, props = find_peaks(clean, prominence=SCR_MIN_AMPLITUDE_US, distance=int(fs),
                            wlen=int(10 * fs))
    amp = clean[idx] - clean[props["left_bases"]]
    thr = np.maximum(SCR_MIN_AMPLITUDE_US, SCR_MIN_RELATIVE * np.abs(tonic[idx]))
    keep = amp >= thr
    return idx[keep], amp[keep]


# --------------------------------------------------------------------------
# Spectral helpers
# --------------------------------------------------------------------------

def _bandpass(x, fs, lo, hi, order=3):
    b, a = butter(order, [lo / (fs / 2), hi / (fs / 2)], "band")
    return filtfilt(b, a, x - np.mean(x))


def dominant_frequency(x: np.ndarray, fs: float, band=CARDIAC_BAND_HZ) -> tuple[float, float]:
    """Dominant frequency (Hz) inside ``band`` and its spectral concentration:
    share of in-band power within +/-0.1 Hz of the peak (and its 1st harmonic).
    Concentration near 1 = clean periodic signal; near 0 = broadband noise."""
    if len(x) < fs * 8 or np.allclose(x, x[0]):
        return np.nan, np.nan
    y = _bandpass(x, fs, band[0] * 0.8, min(band[1] * 1.3, fs / 2 * 0.95))
    f, p = welch(y, fs=fs, nperseg=min(len(y), int(fs * 16)), noverlap=None)
    m = (f >= band[0]) & (f <= band[1])
    if not m.any() or p[m].sum() == 0:
        return np.nan, np.nan
    f0 = f[m][np.argmax(p[m])]
    near = (np.abs(f - f0) <= 0.1) | (np.abs(f - 2 * f0) <= 0.1)
    full = (f >= band[0]) & (f <= min(2 * band[1], fs / 2))
    return float(f0), float(p[near & full].sum() / p[full].sum())


# --------------------------------------------------------------------------
# Session-level preparation (computed once, sliced per window)
# --------------------------------------------------------------------------

def prepare_session(session: Session, invalid: set[str] | None = None) -> dict:
    """Arrays on the session clock (seconds from the EDA start).
    ``invalid`` lists signals to blank for the whole session (repairs.py)."""
    sig = session.signals
    t0 = sig["EDA"].start
    out = {"invalid": set(invalid or ())}
    eda = sig["EDA"].data.EDA.to_numpy()
    comp = eda_components(eda)
    pk, amp = scr_peaks(comp["clean"].to_numpy(), comp["tonic"].to_numpy())
    out["eda_t"] = np.arange(len(eda)) / 4.0
    out["eda"] = comp
    out["eda_raw"] = eda
    out["scr_t"] = pk / 4.0
    out["scr_amp"] = amp

    temp = sig["TEMP"].data.TEMP.to_numpy().astype(float)
    out["temp_t"] = np.arange(len(temp)) / 4.0
    out["temp"] = np.where(temp > TEMP_FAULT_C, np.nan, temp)
    if "TEMP" in out["invalid"]:
        out["temp"][:] = np.nan

    hr = sig["HR"]
    out["hr_t"] = hr.data.index.to_numpy() + (hr.start - t0).total_seconds()
    out["hr"] = hr.data.HR.to_numpy()

    out["bvp"] = sig["BVP"].data.BVP.to_numpy()
    acc = sig["ACC"].data
    out["acc_mag"] = acc_magnitude_g(acc).to_numpy()
    out["acc_sat"] = (acc.abs() >= 127).any(axis=1).to_numpy()

    if session.ibi is not None and len(session.ibi) and "IBI" not in out["invalid"]:
        out["ibi_t"] = session.ibi.t_s.to_numpy()
        out["ibi"] = session.ibi.ibi_s.to_numpy()
    else:
        out["ibi_t"] = np.array([])
        out["ibi"] = np.array([])
    out["duration_s"] = sig["EDA"].duration_s
    return out


def _slope_per_min(t, y):
    m = np.isfinite(y)
    if m.sum() < 4:
        return np.nan
    return float(np.polyfit(t[m] / 60.0, y[m], 1)[0])


def window_features(p: dict, start: float, end: float) -> dict:
    """Features for one window [start, end) in seconds from recording start."""
    f = {}
    dur_min = (end - start) / 60.0

    # --- cardiovascular: Empatica HR -------------------------------------
    m = (p["hr_t"] >= start) & (p["hr_t"] < end)
    h = p["hr"][m]
    f["hr_mean"] = float(np.mean(h)) if m.any() else np.nan
    f["hr_max"] = float(np.max(h)) if m.any() else np.nan
    f["hr_slope"] = _slope_per_min(p["hr_t"][m], h) if m.sum() > 3 else np.nan

    # --- BVP spectral descriptors (quality, independent HR estimate) -------
    b = p["bvp"][int(start * 64):int(end * 64)]
    f0, conc = dominant_frequency(b, 64)
    f["hr_bvp_spectral"] = f0 * 60 if np.isfinite(f0) else np.nan
    f["bvp_sqi"] = conc

    # --- Empatica IBI -------------------------------------------------------
    m = (p["ibi_t"] >= start) & (p["ibi_t"] < end)
    ibi = p["ibi"][m]
    f["ibi_n"] = int(m.sum())
    f["ibi_coverage"] = float(ibi.sum() / (end - start)) if m.any() else 0.0
    f["hr_ibi"] = float(60 / np.median(ibi)) if m.sum() >= 3 else np.nan

    # --- movement --------------------------------------------------------
    a = p["acc_mag"][int(start * 32):int(end * 32)]
    if len(a) >= 64:
        dyn = pd.Series(a).rolling(32, min_periods=16).std().to_numpy()
        f["acc_movement"] = float(np.nanmean(dyn))
        f["acc_enmo"] = float(np.mean(np.maximum(a - 1.0, 0)))
        fa, conc_a = dominant_frequency(a, 32, band=(0.7, 4.0))
        f["acc_dom_freq_per_min"] = fa * 60 if np.isfinite(fa) else np.nan
        f["acc_periodicity"] = conc_a
        f["acc_saturated_frac"] = float(p["acc_sat"][int(start * 32):int(end * 32)].mean())
    else:
        for k in ("acc_movement", "acc_enmo", "acc_dom_freq_per_min", "acc_periodicity", "acc_saturated_frac"):
            f[k] = np.nan

    # --- EDA ---------------------------------------------------------------
    i0, i1 = int(start * 4), int(end * 4)
    tonic = p["eda"]["tonic"].to_numpy()[i0:i1]
    clean = p["eda"]["clean"].to_numpy()[i0:i1]
    t = p["eda_t"][i0:i1]
    f["eda_tonic_mean"] = float(np.mean(tonic)) if len(tonic) else np.nan
    f["eda_tonic_slope"] = _slope_per_min(t, tonic) if len(tonic) > 4 else np.nan
    f["eda_clean_sd"] = float(np.std(clean)) if len(clean) else np.nan
    m = (p["scr_t"] >= start) & (p["scr_t"] < end)
    f["eda_scr_rate"] = float(m.sum() / dur_min)
    f["eda_scr_amp"] = float(np.mean(p["scr_amp"][m])) if m.any() else 0.0
    f["eda_low_contact_frac"] = float((p["eda_raw"][i0:i1] < 0.05).mean()) if len(t) else np.nan

    # --- skin temperature ------------------------------------------------
    tt = p["temp"][i0:i1]
    f["temp_mean"] = float(np.nanmean(tt)) if np.isfinite(tt).any() else np.nan
    f["temp_slope"] = _slope_per_min(p["temp_t"][i0:i1], tt) if len(tt) > 4 else np.nan
    f["temp_valid_frac"] = float(np.isfinite(tt).mean()) if len(tt) else np.nan

    # --- whole-session invalidations --------------------------------------
    inv = p["invalid"]
    blank = []
    if "HR" in inv:
        blank += ["hr_mean", "hr_max", "hr_slope"]
    if "BVP" in inv:
        blank += ["hr_bvp_spectral", "bvp_sqi"]
    if "ACC" in inv:
        blank += ["acc_movement", "acc_enmo", "acc_dom_freq_per_min", "acc_periodicity"]
    for k in blank:
        f[k] = np.nan
    return f


# --------------------------------------------------------------------------
# HRV (segment level only; never on 30-s windows)
# --------------------------------------------------------------------------

def hrv_time_domain(ibi_t: np.ndarray, ibi: np.ndarray, start: float, end: float,
                    min_beats: int = 60, min_coverage: float = 0.5) -> dict:
    """RMSSD / SDNN / mean NN from Empatica IBIs inside [start, end).

    Only *consecutive* beats are differenced (a gap breaks the chain), beats
    outside 0.3-2.0 s and successive changes >20% are removed. Returns NaNs
    unless the segment has >= ``min_beats`` clean beats and coverage
    >= ``min_coverage``.
    """
    m = (ibi_t >= start) & (ibi_t < end)
    t, d = ibi_t[m], ibi[m]
    out = dict(hrv_n_beats=int(len(d)), hrv_coverage=float(d.sum() / (end - start)) if len(d) else 0.0,
               rmssd_ms=np.nan, sdnn_ms=np.nan, mean_nn_ms=np.nan)
    if len(d) < min_beats or out["hrv_coverage"] < min_coverage:
        return out
    ok = (d > 0.3) & (d < 2.0)
    t, d = t[ok], d[ok]
    # consecutive = next beat time equals previous beat time + its IBI (within 1/64 s)
    consecutive = np.abs(np.diff(t) - d[1:]) < 0.02
    succ = np.abs(np.diff(d)) / d[:-1] <= 0.2
    diffs = np.diff(d)[consecutive & succ]
    if len(diffs) < min_beats // 2:
        return out
    out.update(rmssd_ms=float(np.sqrt(np.mean(diffs ** 2)) * 1000),
               sdnn_ms=float(np.std(d) * 1000), mean_nn_ms=float(np.mean(d) * 1000))
    return out
