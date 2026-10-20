"""Export the data behind the interactive charts of the project site.

    python scripts/site/export_site_data.py

Reads data/processed (outputs of notebooks 02-07) and writes
site/assets/data/site_data.json. Confusion matrices need per-window LOSO
predictions, which are recomputed here (random forest, same settings as
notebook 07) and cached in data/processed/clf_loso_predictions.csv.
"""
from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

import numpy as np
import pandas as pd

from src.features.profiles import summarise
from src.models import classify as K
from src.signals.quality import masked_features

PROC = ROOT / "data" / "processed"
OUT = ROOT / "site" / "assets" / "data" / "site_data.json"


def r(x, k=3):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), k)


def records(df, k=3):
    out = []
    for row in df.to_dict(orient="records"):
        out.append({c: (r(v, k) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (np.integer,)) else v))
                    for c, v in row.items()})
    return out


def main():
    data = {}
    w = pd.read_csv(PROC / "windows.csv")
    m = masked_features(w)

    # 1 · HR validity by state (stacked reasons)
    order = ["SEATED_BASELINE", "SEATED_REST", "STRESS_TASK", "UNLOADED_PEDALLING", "AEROBIC_STAGE", "SPRINT", "POST_EXERCISE_REST"]
    ct = pd.crosstab(w.state, w.hr_fail_reason, normalize="index").reindex(order).fillna(0)
    data["hr_validity"] = [{"state": s, **{k: r(ct.loc[s, k]) for k in ct.columns}} for s in order]

    # 2 · Event-locked responses
    ev = {}
    for name, fn in [("tmct", "event_traces_tmct.csv"), ("sprint", "event_traces_sprint.csv")]:
        s = summarise(pd.read_csv(PROC / fn))
        ev[name] = {sig: records(s[s.signal == sig][["t", "mean", "low", "high", "n"]].dropna(subset=["mean"]), 4)
                    for sig in ["HR", "EDA", "Movement", "TEMP"]}
    data["event_locked"] = ev

    # 3 · Change from rest
    vr = pd.read_csv(PROC / "stats_vs_rest.csv")
    data["vs_rest"] = records(vr[["feature", "state", "n", "mean_diff", "ci_low", "ci_high", "dz", "p_holm"]], 4)

    # 4 · Aerobic V1 stages, per participant
    a = m[(m.condition == "AEROBIC") & (m.cohort == "V1") & m.segment.str.match(r"rpm_\d+$")].copy()
    a["rpm"] = a.segment.str[4:].astype(int)
    per = a.groupby(["subject_id", "rpm"])[["hr_mean", "eda_tonic_mean", "temp_mean", "acc_movement"]].mean().reset_index()
    data["aerobic"] = records(per, 3)

    # 5 · Individual stress responses
    pm = pd.read_csv(PROC / "participant_state_means.csv")
    hr = pm.pivot_table(index="subject_id", columns="analysis_state", values="hr_mean")
    eda = pm.pivot_table(index="subject_id", columns="analysis_state", values="eda_tonic_mean")
    ind = pd.DataFrame({"dHR": hr.STRESS_TMCT - hr.REST_SEATED, "dEDA": eda.STRESS_TMCT - eda.REST_SEATED}).reset_index()
    ind["cohort"] = np.where(ind.subject_id.str.startswith("S"), "V1", "V2")
    data["individual"] = records(ind, 3)

    # 6 · Multimodal profile (participant medians per state)
    states = ["REST_SEATED", "STRESS_TMCT", "STRESS_RECOVERY", "AEROBIC_MODERATE", "AEROBIC_PEAK", "SPRINT", "POST_SPRINT", "POST_EXERCISE_REST"]
    feats = ["hr_mean", "eda_tonic_mean", "eda_scr_rate", "temp_slope", "acc_movement"]
    med = pm.groupby("analysis_state")[feats].median().reindex(states)
    nval = pm.groupby("analysis_state")[feats].count().reindex(states)
    med = med.where(nval >= 10)
    data["profile"] = {"states": states, "features": feats,
                       "values": [[r(med.loc[s, f], 3) for f in feats] for s in states]}

    # 7 · ICC
    icc = pd.read_csv(PROC / "stats_icc.csv").set_index("feature")
    data["icc"] = {"features": list(icc.index), "states": list(icc.columns),
                   "values": [[r(icc.loc[f, s], 2) for s in icc.columns] for f in icc.index]}

    # 8 · Classification
    data["leakage"] = records(pd.read_csv(PROC / "clf_leakage_demo.csv")[["validation", "macro_f1", "balanced_accuracy"]])
    data["ablation"] = records(pd.read_csv(PROC / "clf_ablation.csv")[["feature_set", "macro_f1", "macro_f1_low", "macro_f1_high", "balanced_accuracy"]])
    data["shortcut"] = records(pd.read_csv(PROC / "clf_missingness_shortcut.csv")[["feature_set", "macro_f1", "balanced_accuracy", "recall_ANAEROBIC"]])
    sr = pd.read_csv(PROC / "clf_stress_vs_rest.csv")
    data["stress_rest"] = records(sr[sr.model == "Random forest"][["feature_set", "macro_f1", "macro_f1_low", "macro_f1_high", "balanced_accuracy"]])

    pred_file = PROC / "clf_loso_predictions.csv"
    d = pd.read_csv(PROC / "classification_windows.csv")
    if pred_file.exists():
        preds = pd.read_csv(pred_file)
    else:
        rf = K.make_models()["Random forest"]
        preds = pd.DataFrame({"subject_id": d.subject_id, "target": d.target})
        for name in ["Movement (ACC)", "Physiology (HR+EDA+TEMP)", "All signals"]:
            preds[name] = K.cv_predict(rf, d[K.FEATURE_SETS[name]], d.target, d.subject_id)
            print("predicted", name)
        preds.to_csv(pred_file, index=False)
    data["confusion"] = {name: K.confusion(preds.target, preds[name]).values.tolist()
                         for name in ["Movement (ACC)", "Physiology (HR+EDA+TEMP)", "All signals"]}
    data["classes"] = K.CLASSES

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False), encoding="utf8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
