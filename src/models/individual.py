"""Individual responses (Phase 7): who really responded, and how hard did each
person actually work?

Sports-science framework for single-person decisions (Hopkins 2000; Swinton et
al. 2018; Atkinson & Batterham 2015):

* **Typical error (TE)**: how much one person's block mean changes between two
  comparable rest blocks of the same session. TE = SD(rest_a - rest_b) / sqrt(2),
  pooled across participants.
* **Smallest worthwhile change (SWC)**: 0.2 x between-person SD at seated rest.
* A response (task - rest) is compared with the SWC using a 90% interval of
  +/- 1.645 x sqrt(2) x TE, because both blocks carry measurement error.
* **True individual-response SD**: sqrt(SD(responses)^2 - 2 TE^2). Above zero
  means people genuinely differ in how they respond, beyond measurement noise.

Relative exercise intensity uses age-predicted HRmax (Tanaka et al. 2001) and
ACSM intensity categories (Garber et al. 2011).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

Z90 = 1.645
SWC_FACTOR = 0.2

# Stress-day blocks: seated baseline, TMCT, and the second half of each rest
# (the same definitions as notebook 06).
STRESS_BLOCKS = {"REST_SEATED": "rest", "STRESS_TMCT": "task"}
REST_PAIR = ("first_rest", "second_rest")

RESPONSE = "Clear response"
NO_RESPONSE = "No meaningful response"
UNCLEAR = "Unclear"
CATEGORIES = [RESPONSE, UNCLEAR, NO_RESPONSE]

# ACSM (Garber et al. 2011) relative-intensity categories
ACSM_HRMAX = [(0, 57, "very light"), (57, 64, "light"), (64, 77, "moderate"),
              (77, 96, "vigorous"), (96, np.inf, "near-maximal")]
ACSM_HRR = [(-np.inf, 30, "very light"), (30, 40, "light"), (40, 60, "moderate"),
            (60, 90, "vigorous"), (90, np.inf, "near-maximal")]


def stress_blocks(m: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Participant x block means on the stress day: rest, task, rest_a, rest_b."""
    s = m[m.condition == "STRESS"]
    main = (s[s.analysis_state.isin(STRESS_BLOCKS)]
            .groupby(["subject_id", "analysis_state"])[features].mean()
            .rename(index=STRESS_BLOCKS, level=1))
    rec = s[(s.analysis_state == "STRESS_RECOVERY") & s.segment.isin(REST_PAIR)]
    rec = (rec.groupby(["subject_id", "segment"])[features].mean()
           .rename(index={REST_PAIR[0]: "rest_a", REST_PAIR[1]: "rest_b"}, level=1))
    out = pd.concat([main, rec]).sort_index()
    out.index.names = ["subject_id", "block"]
    return out


def typical_error(a: np.ndarray, b: np.ndarray, n_boot: int = 5000, seed: int = 0) -> dict:
    """Typical error from paired repeat measurements (SD of differences / sqrt 2)."""
    d = np.asarray(a, float) - np.asarray(b, float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 5:
        return dict(te=np.nan, te_low=np.nan, te_high=np.nan, n=n)
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(n_boot, n), replace=True).std(axis=1, ddof=1) / np.sqrt(2)
    return dict(te=d.std(ddof=1) / np.sqrt(2), te_low=np.percentile(boots, 2.5),
                te_high=np.percentile(boots, 97.5), n=n)


def smallest_worthwhile_change(rest_values: np.ndarray, factor: float = SWC_FACTOR) -> float:
    """0.2 x between-person SD of the resting values (Hopkins)."""
    v = np.asarray(rest_values, float)
    return factor * np.nanstd(v, ddof=1)


def classify(response: np.ndarray, te: float, swc: float, z: float = Z90) -> pd.DataFrame:
    """90% interval around each person's response and a three-way category:
    clear response (interval entirely above +SWC), no meaningful response
    (entirely below +SWC) or unclear (interval contains +SWC)."""
    r = np.asarray(response, float)
    half = z * np.sqrt(2) * te
    low, high = r - half, r + half
    cat = np.where(~np.isfinite(r), None,
                   np.where(low > swc, RESPONSE, np.where(high < swc, NO_RESPONSE, UNCLEAR)))
    return pd.DataFrame({"response": r, "ci90_low": low, "ci90_high": high, "category": cat})


def individual_response_sd(response: np.ndarray, rest_diff: np.ndarray,
                           n_boot: int = 5000, seed: int = 0) -> dict:
    """SD of true individual responses: sqrt(SD_resp^2 - SD_restdiff^2), where
    SD_restdiff = sqrt(2) x TE. A negative variance (returned as a negative SD)
    means the observed spread is no larger than measurement noise.
    Bootstrap resamples participants for both terms independently."""
    r = np.asarray(response, float); r = r[np.isfinite(r)]
    d = np.asarray(rest_diff, float); d = d[np.isfinite(d)]

    def sd_ir(rr, dd):
        v = rr.std(ddof=1) ** 2 - dd.std(ddof=1) ** 2
        return np.sign(v) * np.sqrt(abs(v))

    rng = np.random.default_rng(seed)
    boots = np.array([sd_ir(rng.choice(r, len(r)), rng.choice(d, len(d))) for _ in range(n_boot)])
    return dict(sd_response=r.std(ddof=1), sd_noise=d.std(ddof=1), sd_ir=sd_ir(r, d),
                sd_ir_low=np.percentile(boots, 2.5), sd_ir_high=np.percentile(boots, 97.5),
                n_response=len(r), n_noise=len(d))


def hrmax_tanaka(age) -> np.ndarray:
    return 208 - 0.7 * np.asarray(age, float)


def acsm_category(pct: float, table=ACSM_HRMAX) -> str | None:
    if not np.isfinite(pct):
        return None
    return next(lab for lo, hi, lab in table if lo <= pct < hi)


def relative_intensity(hr: pd.Series, age: pd.Series, hr_rest: pd.Series) -> pd.DataFrame:
    """%HRmax and %HRR (Karvonen) per participant, with ACSM categories."""
    df = pd.DataFrame({"hr": hr, "age": age, "hr_rest": hr_rest})
    df["hrmax_pred"] = hrmax_tanaka(df.age)
    df["pct_hrmax"] = 100 * df.hr / df.hrmax_pred
    df["pct_hrr"] = 100 * (df.hr - df.hr_rest) / (df.hrmax_pred - df.hr_rest)
    df["acsm_hrmax"] = df.pct_hrmax.map(acsm_category)
    df["acsm_hrr"] = df.pct_hrr.map(lambda v: acsm_category(v, ACSM_HRR))
    return df


# --------------------------------------------------------------------------
# Assembly: one row per participant, shared by notebook 08, the site and Kaggle

SIGNALS = {"hr_mean": "Heart rate (bpm)", "eda_log": "EDA tonic (log10 µS)",
           "eda_scr_rate": "SCR rate (per min)"}
MIN_PEAK_WINDOWS = 3


def noise_summary(blocks: pd.DataFrame, signals=tuple(SIGNALS)) -> pd.DataFrame:
    """TE, SWC, repeats needed and true individual-response SD per signal."""
    wide = blocks.unstack("block")
    rows = []
    for f in signals:
        x = wide[f]
        te = typical_error(x.rest_a, x.rest_b)
        te_cons = typical_error(x.rest, x.rest_a)  # conservative: baseline vs first recovery
        swc = smallest_worthwhile_change(x.rest)
        resp = (x.task - x.rest).to_numpy()
        sdir = individual_response_sd(resp, (x.rest_a - x.rest_b).to_numpy())
        rows.append(dict(signal=f, label=SIGNALS[f], swc=swc, **te, te_conservative=te_cons["te"],
                         mean_response=np.nanmean(resp),
                         repeats_needed=int(np.ceil((Z90 * np.sqrt(2) * te["te"] / swc) ** 2)),
                         **sdir))
    return pd.DataFrame(rows).set_index("signal")


def profile_type(hr_category, eda_category) -> str | None:
    """Response channel(s) with a clear response: heart, sweat, both or neither."""
    if not (isinstance(hr_category, str) and isinstance(eda_category, str)):
        return None
    h, e = hr_category == RESPONSE, eda_category == RESPONSE
    return "heart and sweat" if h and e else "heart only" if h else "sweat only" if e else "no clear response"


def build_profiles(m: pd.DataFrame, info: pd.DataFrame, stress_levels: dict[str, pd.DataFrame]):
    """Per-participant profile table plus the noise summary it was classified with.

    ``m`` is the quality-masked window table with an ``eda_log`` column."""
    feats = list(SIGNALS) + ["acc_movement"]
    blocks = stress_blocks(m, feats)
    noise = noise_summary(blocks)
    wide = blocks.unstack("block")

    prof = pd.DataFrame(index=sorted(m.subject_id.unique()))
    prof.index.name = "subject_id"
    inf = info.set_index("subject_id")
    prof["cohort"] = np.where(prof.index.str.startswith("S"), "V1", "V2")
    prof["sex"] = inf["Gender"].reindex(prof.index)
    prof["age"] = inf["Age"].reindex(prof.index)
    prof["active"] = inf["Does physical activity regularly?"].reindex(prof.index)

    for f in SIGNALS:
        x = wide[f]
        c = classify((x.task - x.rest).to_numpy(), noise.loc[f, "te"], noise.loc[f, "swc"])
        c.index = x.index
        prof[f"{f}_rest"] = x.rest
        for col in c.columns:
            prof[f"{f}_{col}"] = c[col]
    prof["eda_ratio"] = 10 ** prof["eda_log_response"]
    prof["profile"] = [profile_type(h, e) for h, e in zip(prof.hr_mean_category, prof.eda_log_category)]
    prof["movement_change"] = wide["acc_movement"].task - wide["acc_movement"].rest

    sr = pd.concat([d[["Baseline", "TMCT"]] for d in stress_levels.values()])
    prof["selfreport_change"] = (sr.TMCT - sr.Baseline).reindex(prof.index)

    # Signal availability: share of quality-valid HR windows per condition
    valid = m.assign(ok=m.hr_mean.notna()).groupby(["subject_id", "condition"]).ok.mean().unstack()
    for cond in ["STRESS", "AEROBIC", "ANAEROBIC"]:
        prof[f"hr_valid_{cond.lower()}"] = valid.get(cond)

    # Relative intensity (age-predicted HRmax) with reliability flags
    hr = m.groupby(["subject_id", "analysis_state"]).hr_mean.mean().unstack()
    npk = m[m.analysis_state == "AEROBIC_PEAK"].groupby("subject_id").hr_mean.count()
    stage = m[m.analysis_state == "AEROBIC_PEAK"].groupby("subject_id").segment.first()
    for st, short in [("AEROBIC_MODERATE", "moderate"), ("AEROBIC_PEAK", "peak"), ("POST_SPRINT", "post_sprint")]:
        ri = relative_intensity(hr.get(st), prof.age, hr.get("REST_SEATED")).reindex(prof.index)
        prof[f"hr_{short}"] = ri.hr
        prof[f"pct_hrmax_{short}"] = ri.pct_hrmax
        prof[f"acsm_{short}"] = ri.acsm_hrmax
    prof["hrmax_pred"] = hrmax_tanaka(prof.age)
    prof["peak_stage"] = stage.reindex(prof.index)
    prof["peak_valid_windows"] = npk.reindex(prof.index).fillna(0).astype(int)
    prof["peak_enough_data"] = prof.peak_valid_windows >= MIN_PEAK_WINDOWS
    prof["peak_above_moderate"] = prof.hr_peak >= prof.hr_moderate
    prof["peak_reliable"] = (prof.peak_enough_data & prof.peak_above_moderate.fillna(True)
                             & prof.pct_hrmax_peak.notna())
    return prof, noise
