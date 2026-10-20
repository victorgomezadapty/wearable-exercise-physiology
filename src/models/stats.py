"""Participant-level statistics (Phase 5).

The participant is the experimental unit: windows are first averaged within
participant x state, and every test/CI is computed across participants.
"""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats


def participant_means(df: pd.DataFrame, features: list[str], by: list[str]) -> pd.DataFrame:
    """Mean of each feature per participant x ``by`` (NaNs ignored), plus the
    number of valid windows behind each value."""
    g = df.groupby(["subject_id", *by])
    out = g[features].mean()
    counts = g[features].count().add_prefix("n_")
    return out.join(counts).reset_index()


def holm(pvals: pd.Series) -> pd.Series:
    p = pvals.to_numpy(dtype=float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    running = 0.0
    m = np.isfinite(p).sum()
    for rank, i in enumerate(order):
        if not np.isfinite(p[i]):
            adj[i] = np.nan
            continue
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return pd.Series(adj, index=pvals.index)


def paired_effect(a: np.ndarray, b: np.ndarray, n_boot: int = 5000, seed: int = 0) -> dict:
    """Paired comparison b - a across participants.

    Returns mean difference with a bootstrap 95% CI, Cohen's d_z (mean diff /
    SD of diffs) with bootstrap CI, Wilcoxon signed-rank p, and n.
    """
    d = (np.asarray(b, float) - np.asarray(a, float))
    d = d[np.isfinite(d)]
    n = len(d)
    out = dict(n=n, mean_diff=np.nan, ci_low=np.nan, ci_high=np.nan, dz=np.nan,
               dz_low=np.nan, dz_high=np.nan, p_wilcoxon=np.nan)
    if n < 5:
        return out
    rng = np.random.default_rng(seed)
    boots = rng.choice(d, size=(n_boot, n), replace=True)
    bm = boots.mean(axis=1)
    bsd = boots.std(axis=1, ddof=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        bdz = np.where(bsd > 0, bm / bsd, np.nan)
    out.update(mean_diff=d.mean(), ci_low=np.percentile(bm, 2.5), ci_high=np.percentile(bm, 97.5),
               dz=d.mean() / d.std(ddof=1) if d.std(ddof=1) > 0 else np.nan,
               dz_low=np.nanpercentile(bdz, 2.5), dz_high=np.nanpercentile(bdz, 97.5))
    if np.any(d != 0):
        out["p_wilcoxon"] = stats.wilcoxon(d).pvalue
    return out


def pairwise_states(pm: pd.DataFrame, feature: str, states: list[str], state_col: str = "state") -> pd.DataFrame:
    """All pairwise paired comparisons between states for one feature."""
    wide = pm.pivot_table(index="subject_id", columns=state_col, values=feature)
    rows = []
    for i, a in enumerate(states):
        for b in states[i + 1:]:
            if a in wide and b in wide:
                pair = wide[[a, b]].dropna()
                rows.append(dict(feature=feature, state_a=a, state_b=b,
                                 **paired_effect(pair[a].to_numpy(), pair[b].to_numpy())))
    res = pd.DataFrame(rows)
    if len(res):
        res["p_holm"] = holm(res.p_wilcoxon)
    return res


def _fit_mixed(formula: str, d: pd.DataFrame):
    """Fit a random-intercept LMM, trying several optimisers; None if all fail."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for method in ("lbfgs", "powell", "nm"):
            try:
                return smf.mixedlm(formula, d, groups=d["subject_id"]).fit(reml=True, method=method)
            except (np.linalg.LinAlgError, ValueError):
                continue
    return None


def mixed_model(df: pd.DataFrame, feature: str, fixed: str = "C(state) + C(cohort)") -> dict:
    """Random-intercept LMM: feature ~ fixed + (1 | subject). Returns the fitted
    result plus the intraclass correlation (between-person share of variance)."""
    d = df[["subject_id", feature] + [c for c in ("state", "cohort") if c in df]].dropna()
    res = _fit_mixed(f"{feature} ~ {fixed}", d)
    if res is None:
        raise RuntimeError(f"mixed model failed for {feature}")
    var_between = float(res.cov_re.iloc[0, 0])
    var_within = float(res.scale)
    return dict(result=res, n_obs=len(d), n_subjects=d.subject_id.nunique(),
                icc=var_between / (var_between + var_within) if (var_between + var_within) > 0 else np.nan)


def icc_within_state(df: pd.DataFrame, feature: str) -> float:
    """ICC(1) (one-way ANOVA estimator, unbalanced groups) on windows *within
    one state*: share of window-to-window variance that is between
    participants. Truncated at 0. The ANOVA estimator is used instead of an
    LMM because the LMM optimiser converged to the zero boundary for
    small-variance features."""
    d = df[["subject_id", feature]].dropna()
    g = d.groupby("subject_id")[feature]
    n = g.size()
    k, N = len(n), int(n.sum())
    if k < 5 or N <= k:
        return np.nan
    gm = d[feature].mean()
    msb = float((n * (g.mean() - gm) ** 2).sum() / (k - 1))
    msw = float(((d[feature] - g.transform("mean")) ** 2).sum() / (N - k))
    k0 = (N - float((n ** 2).sum()) / N) / (k - 1)
    denom = msb + (k0 - 1) * msw
    return max(0.0, (msb - msw) / denom) if denom > 0 else np.nan


def repeated_measures_corr(df: pd.DataFrame, x: str, y: str, subject: str = "subject_id") -> dict:
    """Bakdash & Marusich (2017) repeated-measures correlation: within-subject
    association after removing each subject's mean."""
    d = df[[subject, x, y]].dropna()
    d = d[d.groupby(subject)[x].transform("count") >= 3]
    xc = d[x] - d.groupby(subject)[x].transform("mean")
    yc = d[y] - d.groupby(subject)[y].transform("mean")
    n, k = len(d), d[subject].nunique()
    r = float(np.corrcoef(xc, yc)[0, 1]) if n > 2 else np.nan
    dof = n - k - 1
    t = r * np.sqrt(dof / (1 - r ** 2)) if abs(r) < 1 else np.inf
    p = 2 * stats.t.sf(abs(t), dof)
    return dict(r_rm=r, dof=dof, p=p, n_obs=n, n_subjects=k)
