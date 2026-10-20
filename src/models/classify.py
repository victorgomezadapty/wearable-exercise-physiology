"""Participant-grouped classification (Phase 6).

Every evaluation holds out whole participants: no window of a test
participant is ever seen during training (LeaveOneGroupOut by subject_id).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

CLASSES = ["STRESS", "AEROBIC", "ANAEROBIC"]

FEATURE_SETS = {
    "Movement (ACC)": ["acc_movement", "acc_enmo", "acc_dom_freq_per_min", "acc_periodicity"],
    "Heart rate": ["hr_mean", "hr_max", "hr_slope"],
    "EDA": ["eda_tonic_mean", "eda_tonic_slope", "eda_clean_sd", "eda_scr_rate", "eda_scr_amp"],
    "Skin temperature": ["temp_mean", "temp_slope"],
}
FEATURE_SETS["Physiology (HR+EDA+TEMP)"] = (FEATURE_SETS["Heart rate"] + FEATURE_SETS["EDA"]
                                            + FEATURE_SETS["Skin temperature"])
FEATURE_SETS["All signals"] = FEATURE_SETS["Movement (ACC)"] + FEATURE_SETS["Physiology (HR+EDA+TEMP)"]

FEATURE_LABELS = {
    "acc_movement": "Movement intensity (SD |ACC|)", "acc_enmo": "ACC ENMO",
    "acc_dom_freq_per_min": "Movement rhythm (per min)", "acc_periodicity": "Movement periodicity",
    "hr_mean": "HR mean", "hr_max": "HR max", "hr_slope": "HR slope",
    "eda_tonic_mean": "EDA tonic level", "eda_tonic_slope": "EDA tonic slope", "eda_clean_sd": "EDA variability",
    "eda_scr_rate": "SCR rate", "eda_scr_amp": "SCR amplitude",
    "temp_mean": "Skin temp mean", "temp_slope": "Skin temp slope",
}


def make_models(seed: int = 0) -> dict:
    imp = SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)
    return {
        "Logistic regression": make_pipeline(clone(imp), StandardScaler(),
                                             LogisticRegression(max_iter=2000, class_weight="balanced")),
        "Decision tree (depth 4)": make_pipeline(clone(imp), DecisionTreeClassifier(
            max_depth=4, min_samples_leaf=20, class_weight="balanced", random_state=seed)),
        "Random forest": make_pipeline(clone(imp), RandomForestClassifier(
            n_estimators=300, min_samples_leaf=5, class_weight="balanced", n_jobs=-1, random_state=seed)),
        "Gradient boosting": HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=300, class_weight="balanced", random_state=seed),
    }


def cv_predict(model, X: pd.DataFrame, y: pd.Series, groups: pd.Series, cv=None) -> np.ndarray:
    cv = cv or LeaveOneGroupOut()
    pred = np.empty(len(y), dtype=object)
    for tr, te in cv.split(X, y, groups):
        m = clone(model).fit(X.iloc[tr], y.iloc[tr])
        pred[te] = m.predict(X.iloc[te])
    return pred


def scores(y_true, y_pred, labels=CLASSES) -> dict:
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    out = dict(macro_f1=f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
               balanced_accuracy=balanced_accuracy_score(y_true, y_pred),
               accuracy=float(np.mean(np.asarray(y_true) == np.asarray(y_pred))))
    for c, pi, ri in zip(labels, p, r):
        out[f"precision_{c}"] = pi
        out[f"recall_{c}"] = ri
    return out


def participant_bootstrap(y_true, y_pred, groups, labels=CLASSES, n_boot=2000, seed=0) -> dict:
    """95% CI of macro-F1 and balanced accuracy by resampling participants."""
    df = pd.DataFrame(dict(y=np.asarray(y_true), p=np.asarray(y_pred), g=np.asarray(groups)))
    subjects = df.g.unique()
    by = {s: d for s, d in df.groupby("g")}
    rng = np.random.default_rng(seed)
    f1s, bas = [], []
    for _ in range(n_boot):
        d = pd.concat([by[s] for s in rng.choice(subjects, len(subjects), replace=True)])
        f1s.append(f1_score(d.y, d.p, labels=labels, average="macro", zero_division=0))
        bas.append(balanced_accuracy_score(d.y, d.p))
    return dict(macro_f1_low=np.percentile(f1s, 2.5), macro_f1_high=np.percentile(f1s, 97.5),
                bal_acc_low=np.percentile(bas, 2.5), bal_acc_high=np.percentile(bas, 97.5))


def confusion(y_true, y_pred, labels=CLASSES) -> pd.DataFrame:
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return pd.DataFrame(cm, index=labels, columns=labels)


def leakage_demo(model, X, y, groups, seed=0) -> pd.DataFrame:
    """Same model, two validation schemes: random window split vs grouped."""
    rows = []
    for name, cv in [("Random 5-fold over windows (leaky)", StratifiedKFold(5, shuffle=True, random_state=seed)),
                     ("Leave-one-subject-out", LeaveOneGroupOut())]:
        pred = cv_predict(model, X, y, groups, cv)
        rows.append(dict(validation=name, **scores(y, pred)))
    return pd.DataFrame(rows)


def grouped_permutation_importance(model, X, y, groups, n_splits=5, n_repeats=10, seed=0) -> pd.DataFrame:
    """Permutation importance (drop in macro-F1) on held-out participants,
    averaged over GroupKFold folds."""
    rows = []
    for k, (tr, te) in enumerate(GroupKFold(n_splits).split(X, y, groups)):
        m = clone(model).fit(X.iloc[tr], y.iloc[tr])
        r = permutation_importance(m, X.iloc[te], y.iloc[te], scoring="f1_macro",
                                   n_repeats=n_repeats, random_state=seed, n_jobs=-1)
        rows.append(pd.DataFrame(dict(feature=X.columns, importance=r.importances_mean, fold=k)))
    imp = pd.concat(rows)
    return (imp.groupby("feature").importance.agg(["mean", "std"]).sort_values("mean", ascending=False)
            .reset_index())
