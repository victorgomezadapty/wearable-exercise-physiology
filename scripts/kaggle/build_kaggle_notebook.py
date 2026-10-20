"""Build the condensed, self-contained Kaggle notebook.

    python scripts/kaggle/build_kaggle_notebook.py <out.ipynb>

On Kaggle it reads the dataset `vctorandrsgmezlpez/wearable-stress-exercise-physiology`
(processed tables + src code). Locally, set WEARABLE_DATA_ROOT to a folder with the same layout.
"""
import sys

import nbformat as nbf

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Wearable Physiology: Stress vs Aerobic vs Anaerobic Exercise

**What does a wrist wearable (Empatica E4) really see during acute psychological stress, aerobic cycling and
anaerobic sprints?**

This notebook is a condensed version of a seven-notebook project. It starts from the quality-checked feature tables,
and every step is documented in the full repository.

- 🌐 Project page: https://victorgomezadapty.github.io/wearable-exercise-physiology/
- 💻 Code and full notebooks: https://github.com/victorgomezadapty/wearable-exercise-physiology

**Principles:** physiology before modelling · the participant is the experimental unit · movement is not
physiological state · signal quality is assessed per window, blind to expected results · machine learning is evaluated
only on unseen participants (leave-one-subject-out).

**Data:** Hongn et al., *Wearable Device Dataset from Induced Stress and Structured Exercise Sessions*, PhysioNet
v1.0.1, [doi:10.13026/he0v-tf17](https://doi.org/10.13026/he0v-tf17) (ODC-By). 36 healthy adults: stress n = 36,
aerobic n = 30, anaerobic n = 31; 30 did all three.
""")
code("""
import os, sys, glob, warnings
from pathlib import Path
warnings.filterwarnings("ignore"); os.environ["PYTHONWARNINGS"] = "ignore"

def find_root():
    env = os.environ.get("WEARABLE_DATA_ROOT")
    if env: return Path(env)
    hits = glob.glob("/kaggle/input/**/processed/windows.csv", recursive=True)
    return Path(hits[0]).parent.parent
ROOT = find_root()
sys.path.insert(0, str(ROOT / "code"))
PROC = ROOT / "processed"

import numpy as np, pandas as pd, matplotlib.pyplot as plt
from src.visualization import plots as P
from src.signals.quality import masked_features
from src.models.stats import paired_effect, holm
from src.features.profiles import summarise
from src.models import classify as K
P.set_style(); C = P.COND_COLORS
pd.set_option("display.width", 200); pd.set_option("display.float_format", lambda v: f"{v:,.3f}")
w = pd.read_csv(PROC / "windows.csv")
m = masked_features(w)
print(f"{len(w):,} windows of 30 s · {w.subject_id.nunique()} participants · {w.groupby(['condition','session_id']).ngroups} recordings")
""")

md("""
## 1 · Signal quality first

Empatica's wrist heart rate is often corrupted during cycling: flat, erratic, or locked onto the pedalling rhythm.
Each window's HR is accepted only if the raw PPG has a clean spectral peak (SQI ≥ 0.40), Empatica's HR agrees with that
peak (≤ 10 bpm), and it does not sit on the cadence measured by the accelerometer. The thresholds come from clean seated
data, never from expected results.
""")
code("""
order = ["SEATED_BASELINE", "SEATED_REST", "STRESS_TASK", "UNLOADED_PEDALLING", "AEROBIC_STAGE", "SPRINT", "POST_EXERCISE_REST"]
v = w.groupby("state").hr_valid.mean().reindex(order)
fig, ax = plt.subplots(figsize=(9, 3.4))
cols = [C["STRESS"] if s in ("SEATED_BASELINE", "SEATED_REST", "STRESS_TASK") else C["ANAEROBIC"] if s == "SPRINT" else C["AEROBIC"] for s in order]
ax.barh(range(len(v)), v.values, color=cols, height=0.6)
for i, x in enumerate(v.values): ax.text(x + 0.01, i, f"{x:.0%}", va="center", fontsize=9)
ax.set_yticks(range(len(v)), [s.replace("_", " ").lower() for s in order]); ax.invert_yaxis(); ax.set_xlim(0, 1)
ax.set_title("Share of 30-s windows with a usable heart rate", loc="left"); ax.grid(axis="y", visible=False)
plt.show()
""")
md("Heart rate from the wrist is usable in most seated windows, in fewer than half of aerobic stages, and almost never during an all-out sprint.")

md("""
## 2 · Physiological responses: change from seated rest

Windows are averaged within each participant first. Differences are paired within person, with bootstrap 95% CIs.
Stress contrasts are same-day. Exercise contrasts compare different days (no exercise session contains a resting
baseline).
""")
code("""
m["eda_log"] = np.log10(m.eda_tonic_mean.clip(lower=0.01))
STATES = ["REST_SEATED", "STRESS_TMCT", "AEROBIC_MODERATE", "AEROBIC_PEAK", "POST_SPRINT"]
LABEL = {"STRESS_TMCT": "Stress (TMCT)", "AEROBIC_MODERATE": "Aerobic moderate", "AEROBIC_PEAK": "Aerobic peak", "POST_SPRINT": "Post-sprint 0-2 min"}
SC = {"STRESS_TMCT": C["STRESS"], "AEROBIC_MODERATE": C["AEROBIC"], "AEROBIC_PEAK": C["AEROBIC"], "POST_SPRINT": C["ANAEROBIC"]}
feats = [("hr_mean", "Heart rate (bpm)"), ("eda_log", "EDA tonic (log10 µS)"), ("acc_movement", "Wrist movement (g)")]
pm = m[m.analysis_state.isin(STATES)].groupby(["subject_id", "analysis_state"])[[f for f, _ in feats]].mean().reset_index()
rows = []
for f, _ in feats:
    wide = pm.pivot_table(index="subject_id", columns="analysis_state", values=f)
    for s in STATES[1:]:
        d = wide[["REST_SEATED", s]].dropna()
        rows.append(dict(feature=f, state=s, **paired_effect(d.REST_SEATED.to_numpy(), d[s].to_numpy())))
res = pd.DataFrame(rows)
fig, axes = plt.subplots(1, 3, figsize=(15, 3.6), sharey=True)
for ax, (f, lab) in zip(axes, feats):
    d = res[res.feature == f].reset_index(drop=True)
    for i, r in d.iterrows():
        ax.plot([r.ci_low, r.ci_high], [i, i], color=SC[r.state], lw=3, solid_capstyle="round")
        ax.scatter(r.mean_diff, i, color=SC[r.state], s=45, zorder=3)
        ax.text(1.0, i, f"n={r.n}", transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=8, color=P.TEXT_2)
    ax.axvline(0, color=P.TEXT, lw=0.8); ax.set_title(lab, loc="left", fontsize=10); ax.grid(axis="y", visible=False)
axes[0].set_yticks(range(4), [LABEL[s] for s in STATES[1:]]); axes[0].invert_yaxis()
fig.suptitle("Change from seated rest (participant-paired mean, 95% CI)", x=0.01, ha="left", fontweight="bold"); fig.tight_layout(); plt.show()
res[["feature", "state", "n", "mean_diff", "ci_low", "ci_high", "dz"]].round(3)
""")
md("""
- The **mental-stress task raises HR by about +5 bpm and EDA about 1.6-fold, while wrist movement *decreases***.
  A physiological response with no mechanical cause.
- **Exercise dominates:** about +49 bpm and ~11-fold EDA at the aerobic peak.
""")

md("## 3 · Event-locked responses: stress task vs sprint")
code("""
sig = [("HR", "Δ heart rate (bpm)"), ("EDA", "Δ EDA (µS)"), ("Movement", "Δ movement (g)")]
fig, axes = plt.subplots(2, 3, figsize=(15, 6), sharex=True)
for row, (fn, col, name) in enumerate([("event_traces_tmct.csv", C["STRESS"], "Stress task onset"), ("event_traces_sprint.csv", C["ANAEROBIC"], "Sprint onset")]):
    s = summarise(pd.read_csv(PROC / fn))
    for j, (k, lab) in enumerate(sig):
        ax = axes[row, j]; d = s[s.signal == k]
        ax.fill_between(d.t, d.low, d.high, color=col, alpha=0.22, lw=0); ax.plot(d.t, d["mean"], color=col, lw=2)
        ax.axhline(0, color=P.TEXT_2, lw=0.8); ax.axvline(0, color=P.TEXT_2, lw=0.8)
        if row == 0: ax.set_title(lab, loc="left", fontsize=10)
        if j == 0: ax.set_ylabel(name)
for ax in axes[1]: ax.set_xlabel("s from onset")
fig.tight_layout(); plt.show()
""")
md("""
Stress: HR plateaus at about +6–7 bpm, and EDA climbs while movement stays flat. Sprint: a movement burst, then HR keeps
rising for about a minute after the effort, and EDA rises in a sustained way. Valid wrist HR returns only ~60 s after
the sprint, from 5–15 participants.
""")

md("""
## 4 · Classification on unseen people

Classes: **STRESS** (stress tasks), **AEROBIC** (aerobic stages), **ANAEROBIC** (sprint + first 2 min of recovery).
Leave-one-subject-out. Macro-F1 with participant-bootstrap CIs.
""")
code("""
d = pd.read_csv(PROC / "classification_windows.csv"); y, g = d.target, d.subject_id
rf = K.make_models()["Random forest"]
leak = K.leakage_demo(rf, d[K.FEATURE_SETS["All signals"]], y, g)
print(leak[["validation", "macro_f1", "balanced_accuracy"]].round(3).to_string(index=False))
""")
md("The ~0.17 gap is the model recognising individuals. HR and EDA are highly person-specific (ICC 0.83–0.99), so only participant-grouped validation is meaningful.")
code("""
d["hr_missing"] = d.hr_mean.isna().astype(float)
sets = {"Skin temperature": K.FEATURE_SETS["Skin temperature"], "EDA": K.FEATURE_SETS["EDA"], "Heart rate": K.FEATURE_SETS["Heart rate"],
        "Physiology (HR+EDA+TEMP)": K.FEATURE_SETS["Physiology (HR+EDA+TEMP)"], "Movement (ACC)": K.FEATURE_SETS["Movement (ACC)"],
        "Movement + 'HR missing' flag": K.FEATURE_SETS["Movement (ACC)"] + ["hr_missing"], "All signals": K.FEATURE_SETS["All signals"]}
rows = []
for name, cols in sets.items():
    p = K.cv_predict(rf, d[cols], y, g)
    rows.append(dict(feature_set=name, **K.scores(y, p), **K.participant_bootstrap(y, p, g, n_boot=500)))
abl = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(9.5, 4))
for i, r in abl.iterrows():
    ax.plot([r.macro_f1_low, r.macro_f1_high], [i, i], color=P.TEXT_2, lw=3, solid_capstyle="round")
    ax.scatter(r.macro_f1, i, s=55, color=P.TEXT, zorder=3); ax.text(r.macro_f1_high + 0.01, i, f"{r.macro_f1:.2f}", va="center", fontsize=9)
ax.axvline(1/3, color=P.TEXT_2, lw=0.8); ax.set_yticks(range(len(abl)), abl.feature_set); ax.set_xlim(0.2, 1)
ax.set_xlabel("macro-F1, leave-one-subject-out (95% CI)"); ax.grid(axis="y", visible=False)
ax.set_title("Which signals carry the information?", loc="left"); plt.show()
abl[["feature_set", "macro_f1", "balanced_accuracy", "recall_STRESS", "recall_AEROBIC", "recall_ANAEROBIC"]].round(3)
""")
md("""
- **Combinations beat single signals**, but **movement** is the strongest single modality.
- **Movement plus a binary "HR missing" flag** gets almost as far as all signals. The PPG *failing* during sprints is
  itself a cue: a sensor property, not physiology.
""")
code("""
s2 = m[m.analysis_state.isin(["REST_SEATED", "STRESS_RECOVERY", "STRESS_TMCT", "STRESS_SHORT"])].copy()
s2["target"] = np.where(s2.analysis_state.isin(["STRESS_TMCT", "STRESS_SHORT"]), "STRESS", "REST")
out = []
for name in ["Movement (ACC)", "EDA", "Physiology (HR+EDA+TEMP)"]:
    p = K.cv_predict(rf, s2[K.FEATURE_SETS[name]], s2.target, s2.subject_id)
    sc = K.scores(s2.target, p, labels=["REST", "STRESS"])
    out.append(dict(task="stress vs seated rest", feature_set=name, macro_f1=sc["macro_f1"], balanced_accuracy=sc["balanced_accuracy"]))
pd.DataFrame(out).round(3)
""")
md("""
When movement cannot help (**stress vs seated rest**), **physiology alone detects acute stress in unseen people**
(macro-F1 ≈ 0.65), with EDA as the most informative single signal.

## Take-home

A wrist wearable separates seated stress from cycling mostly by movement. It detects acute stress while sitting from
physiology with modest accuracy, and it struggles to tell aerobic from anaerobic cycling. The physiology is real (a
stress response with the body stiller than at rest; exercise responses an order of magnitude larger), but it is highly
individual, and wrist-PPG heart rate needs quality control before it means anything during exercise.

*Limitations:* small, healthy, young sample. Cohorts confounded with sex and protocol version. No ECG, power or VO₂
reference. The resting reference is on a different day from exercise. No clinical inference.
""")

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, sys.argv[1]); print("ok")
