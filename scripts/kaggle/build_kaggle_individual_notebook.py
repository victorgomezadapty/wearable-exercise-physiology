"""Build the second Kaggle notebook: individual responses, for practitioners.

    python scripts/kaggle/build_kaggle_individual_notebook.py <out.ipynb>

Reads the Kaggle dataset built by build_kaggle_bundle.py (processed/, code/, raw/).
Locally, set WEARABLE_DATA_ROOT to that folder.
"""
import sys

import nbformat as nbf

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""
# Who Really Responded? Individual Stress Responses and Exercise Intensity from a Wrist Wearable

**The group says "+5 bpm under stress". Your client is not the group.**

Most wearable analyses report averages or classifier accuracy. A physiotherapist or coach decides about **one
person**: did *this* client respond, through which channel, how sure can I be, and did the session really reach the
intensity I prescribed? This notebook answers those questions with the toolkit sports science uses for individual
decisions (typical error, smallest worthwhile change, true individual-response variability), applied to an Empatica E4
wrist wearable during a mental-stress task and incremental cycling.

What is new here compared with my [group-level notebook](https://www.kaggle.com/code/vctorandrsgmezlpez/wearable-physiology-stress-vs-exercise):

1. **Signal vs noise, per person**: how much of the spread between people is real, and how much is measurement noise.
2. **Responder classification** with 90% intervals, and **how many repeated tests** a practitioner would need.
3. **Response channels**: heart vs sweat glands vs self-report.
4. **Relative intensity** (% of age-predicted HRmax) with reliability flags for wrist heart rate.
5. **Profile cards** for any participant, and a **reusable template** to apply the same method to your own clients.

- 🌐 Interactive version: https://victorgomezadapty.github.io/wearable-exercise-physiology/individual.html
- 💻 Code: https://github.com/victorgomezadapty/wearable-exercise-physiology (notebook 08, `src/models/individual.py`)

**Data:** Hongn et al., *Wearable Device Dataset from Induced Stress and Structured Exercise Sessions*, PhysioNet
v1.0.1, [doi:10.13026/he0v-tf17](https://doi.org/10.13026/he0v-tf17) (ODC-By). 36 healthy adults aged 18–31.
""")
code("""
import os, sys, glob, warnings
from pathlib import Path
warnings.filterwarnings("ignore"); os.environ["PYTHONWARNINGS"] = "ignore"

def find_root():
    env = os.environ.get("WEARABLE_DATA_ROOT")
    if env: return Path(env)
    hits = glob.glob("/kaggle/input/**/processed/windows.csv", recursive=True)
    if hits:
        return Path(hits[0]).parent.parent
    # Fallback: folders uploaded as zip archives that were not auto-extracted
    import zipfile
    work = Path("/kaggle/working/wearable"); work.mkdir(parents=True, exist_ok=True)
    for z in glob.glob("/kaggle/input/**/*.zip", recursive=True):
        name = Path(z).stem
        if name in ("processed", "code", "interim", "raw"):
            zipfile.ZipFile(z).extractall(work / name)
    return work
ROOT = find_root()
sys.path.insert(0, str(ROOT / "code"))
PROC, META = ROOT / "processed", ROOT / "raw"

import numpy as np, pandas as pd, matplotlib.pyplot as plt
from scipy import stats
from src.visualization import plots as P
from src.signals.quality import masked_features
from src.data.empatica import read_subject_info, read_stress_levels
from src.models import individual as I
P.set_style(); C = P.COND_COLORS
pd.set_option("display.width", 200); pd.set_option("display.float_format", lambda v: f"{v:,.3f}")

w = pd.read_csv(PROC / "windows.csv")
m = masked_features(w)                       # signals failing quality control -> NaN
m["eda_log"] = np.log10(m.eda_tonic_mean.clip(lower=0.01))
prof, noise = I.build_profiles(m, read_subject_info(META), read_stress_levels(META))
CAT_COLORS = {I.RESPONSE: C["STRESS"], I.UNCLEAR: "#bdbab2", I.NO_RESPONSE: P.TEXT_2}
print(f"{len(w):,} quality-checked 30-s windows · {prof.shape[0]} participants")
""")

md("""
## 1 · How much does one person's value move when nothing happens?

The stress session contains two comparable seated rests. The difference between a person's two rests is pure
measurement noise plus normal fluctuation. Its SD / √2 is the **typical error (TE)**. The **smallest worthwhile change
(SWC)** is 0.2 × the between-person SD at rest (Hopkins' convention).
""")
code("""
noise[["label", "te", "te_low", "te_high", "swc", "mean_response"]].round(3)
""")
md("""
For heart rate, the typical error (**2.4 bpm**) is about the same size as the smallest worthwhile change (**2.3 bpm**).
That one fact explains most of what follows: **for an individual, the noise is as large as the effect you care about.**
""")

md("""
## 2 · Is the spread between people real?

If every participant had the same true stress response, the observed responses (task − baseline) would spread no more
than the noise does (rest − rest). The grey curve is the noise, shifted to the group mean. The coloured curve is what
was actually observed.
""")
code("""
blocks = I.stress_blocks(m, list(I.SIGNALS)).unstack("block")
fig, axes = plt.subplots(1, 3, figsize=(15, 3.8))
for ax, f in zip(axes, I.SIGNALS):
    x = blocks[f]
    resp = (x.task - x.rest).dropna()
    rest_diff = (x.rest_a - x.rest_b).dropna()
    grid = np.linspace(min(resp.min(), resp.mean() + rest_diff.min()) * 1.2, max(resp.max(), resp.mean() + rest_diff.max()) * 1.2, 300)
    ax.fill_between(grid, stats.gaussian_kde(rest_diff - rest_diff.mean() + resp.mean())(grid), color="#bdbab2", alpha=0.6, lw=0, label="noise only (rest − rest)")
    ax.plot(grid, stats.gaussian_kde(resp)(grid), color=C["STRESS"], lw=2.4, label="observed (task − baseline)")
    ax.axvline(0, color=P.TEXT, lw=0.8)
    sd = noise.loc[f]
    ax.set_title(f"{sd.label}\\ntrue individual-response SD = {sd.sd_ir:.2f} (95% CI {sd.sd_ir_low:.2f}–{sd.sd_ir_high:.2f})", loc="left", fontsize=9.5)
    ax.set_yticks([]); ax.grid(axis="y", visible=False)
axes[0].legend(fontsize=8, loc="upper left")
fig.suptitle("Observed responses are far wider than measurement noise: people genuinely differ", x=0.01, ha="left", fontweight="bold")
fig.tight_layout(); plt.show()
noise[["label", "mean_response", "sd_response", "sd_noise", "sd_ir", "sd_ir_low", "sd_ir_high"]].round(3)
""")
md("""
**People genuinely respond differently.** The true individual-response SD for heart rate is **7.6 bpm** around a mean
of +5.0 bpm: about one person in four has no true HR rise, and about one in four rises by more than 10 bpm. EDA and
SCR rate show the same pattern. The group mean is a real effect that describes almost nobody.
""")

md("""
## 3 · Who responded? (one test each)

90% interval = response ± 1.645 × √2 × TE. **Clear response**: the whole interval is above +SWC. **No meaningful
response**: the whole interval is below +SWC. Otherwise **unclear**.
""")
code("""
fig, axes = plt.subplots(1, 2, figsize=(13, 8.5))
for ax, f, unit in [(axes[0], "hr_mean", "bpm"), (axes[1], "eda_log", "log10 µS")]:
    d = prof[[f"{f}_response", f"{f}_ci90_low", f"{f}_ci90_high", f"{f}_category"]].dropna().sort_values(f"{f}_response")
    for i, (sid, r) in enumerate(d.iterrows()):
        col = CAT_COLORS[r[f"{f}_category"]]
        ax.plot([r[f"{f}_ci90_low"], r[f"{f}_ci90_high"]], [i, i], color=col, lw=2.2, solid_capstyle="round")
        ax.scatter(r[f"{f}_response"], i, color=col, s=32, zorder=3, edgecolor=P.SURFACE, lw=1.2)
    ax.axvline(0, color=P.TEXT, lw=0.9); ax.axvline(noise.loc[f, "swc"], color=P.TEXT_2, lw=1, ls="--")
    ax.set_yticks(range(len(d)), d.index, fontsize=7.5); ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"stress task − seated baseline ({unit})")
    n = d[f"{f}_category"].value_counts()
    ax.set_title(f"{I.SIGNALS[f]}: clear {n.get(I.RESPONSE, 0)} · unclear {n.get(I.UNCLEAR, 0)} · none {n.get(I.NO_RESPONSE, 0)}", loc="left", fontsize=10)
fig.legend(handles=[plt.Line2D([], [], color=c, lw=3, label=k) for k, c in CAT_COLORS.items()], loc="lower center", ncol=3)
fig.tight_layout(rect=(0, 0.03, 1, 1)); plt.show()
""")
md("""
After one 3–4.5-minute stress task, **9 of 34** participants are clear heart-rate responders, 6 show no meaningful
response and **19 are unclear**. For EDA level it is 9 clear and 25 unclear. The real differences exist (section 2),
but a single short test resolves them for only about one person in four.
""")

md("""
## 4 · How many repeated tests would a practitioner need?

Averaging k tests shrinks the interval by √k. The number of tests needed for the 90% half-width to drop below the SWC:
""")
code("""
k = np.arange(1, 21)
fig, ax = plt.subplots(figsize=(8, 3.8))
for f, ls in zip(I.SIGNALS, ["-", "--", ":"]):
    ax.plot(k, I.Z90 * np.sqrt(2) * noise.loc[f, "te"] / np.sqrt(k) / noise.loc[f, "swc"], ls=ls, lw=2, color=P.TEXT,
            label=f"{I.SIGNALS[f]}: {int(noise.loc[f, 'repeats_needed'])} tests")
ax.axhline(1, color=C["STRESS"], lw=1.5)
ax.set_xlabel("repeated tests averaged"); ax.set_ylabel("90% half-width / SWC"); ax.legend(fontsize=8)
ax.set_title("Below the green line, noise is smaller than the change worth detecting", loc="left")
plt.show()
""")
md("""
About **6 tests for heart rate**, 4 for EDA level and 14 for SCR rate. With a more conservative noise estimate, about
15 for heart rate. **One session is a hypothesis about a person, not a label.**
""")

md("""
## 5 · Same stressor, different channels
""")
code("""
PCOL = {"heart and sweat": "#7a4fd1", "heart only": "#d64f6b", "sweat only": "#2f8fb0", "no clear response": "#bdbab2"}
fig, ax = plt.subplots(figsize=(7.5, 5.5))
for p, col in PCOL.items():
    d = prof[prof.profile == p]
    ax.scatter(d.hr_mean_response, d.eda_ratio, color=col, s=55, edgecolor=P.SURFACE, lw=1.2, label=f"{p} (n = {len(d)})", zorder=3)
ax.set_yscale("log"); ax.set_yticks([0.5, 0.75, 1, 1.5, 2, 3, 4, 6], ["×0.5", "×0.75", "×1", "×1.5", "×2", "×3", "×4", "×6"]); ax.minorticks_off()
ax.axvline(noise.loc["hr_mean", "swc"], color=P.TEXT_2, ls="--", lw=1); ax.axhline(10 ** noise.loc["eda_log", "swc"], color=P.TEXT_2, ls="--", lw=1)
d = prof[["hr_mean_response", "eda_log_response"]].dropna()
ax.set_xlabel("HR response (bpm)"); ax.set_ylabel("EDA level response (× baseline)")
ax.set_title(f"Heart vs sweat responses (Spearman ρ = {stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1]).statistic:.2f})", loc="left")
ax.legend(fontsize=8, loc="upper left"); plt.show()
prof.groupby("profile").selfreport_change.agg(["median", "size"]).rename(columns={"median": "self-report change (median)", "size": "n"})
""")
md("""
Heart and sweat responses are unrelated across people. Of the 15 people with a clear response on either signal, only
**3 respond on both**: **a monitor that watches one channel misses about half of the responders.** Self-reported stress
rises similarly in every profile, so asking does not tell you which channel will respond.
""")

md("""
## 6 · External load ≠ internal load

The cycling protocol prescribes cadences. Relative intensity = HR / (208 − 0.7 × age) (Tanaka et al. 2001). A
final-stage value is labelled **reliable** with ≥ 3 quality-valid 30-s windows and HR not below the moderate stages.
Unreliable values are kept and labelled, never silently removed.
""")
code("""
ex = prof[prof.hr_valid_aerobic.notna() & prof.age.notna()].sort_values("pct_hrmax_peak")
rel = ex[ex.peak_reliable]
print(f"aerobic participants: {len(ex)} · reliable final-stage HR: {len(rel)} · range {rel.pct_hrmax_peak.min():.0f}–{rel.pct_hrmax_peak.max():.0f}% HRmax (median {rel.pct_hrmax_peak.median():.0f}%)")
rel[["sex", "age", "peak_stage", "hr_peak", "pct_hrmax_peak", "acsm_peak", "peak_valid_windows"]].round(1)
""")
md("""
Only **14 of 30** people have a final-stage wrist heart rate a practitioner could use. In them, the **same protocol ended
anywhere between 46% and 91% of predicted HRmax**, from very light to vigorous. Prescribing exercise by external load
alone does not give everyone the same stimulus. (Age-predicted HRmax carries roughly ±10 bpm of individual error.)
""")

md("""
## 7 · Profile cards

Everything above, for one person. Change the ID to see anyone (`S01`–`S18`, `f01`–`f18`).
""")
code("""
def card(sid):
    r = prof.loc[sid]
    verdict = {I.RESPONSE: "clear response", I.UNCLEAR: "unclear", I.NO_RESPONSE: "no meaningful response"}
    age = "age ?" if pd.isna(r.age) else f"{r.age:.0f} y"
    lines = [f"── {sid} · {r.sex}, {age} · cohort {r.cohort} · active: {r.active if isinstance(r.active, str) else '?'}",
             f"   Stress profile: {r.profile}"]
    for f, fmt_ in [("hr_mean", lambda v: f"{v:+.1f} bpm"), ("eda_log", lambda v: f"×{10 ** v:.2f}"), ("eda_scr_rate", lambda v: f"{v:+.1f} /min")]:
        v = r[f"{f}_response"]
        lines.append(f"   {I.SIGNALS[f]:<22} {'no data' if pd.isna(v) else fmt_(v):>10}  → {verdict.get(r[f'{f}_category'], 'no data')}")
    lines.append(f"   Self-reported stress change: {r.selfreport_change:+.0f}" if pd.notna(r.selfreport_change) else "   Self-report: –")
    if pd.isna(r.hr_valid_aerobic):
        lines.append("   Aerobic session: none")
    elif r.peak_reliable:
        lines.append(f"   Aerobic final stage: {r.pct_hrmax_peak:.0f}% HRmax ({r.acsm_peak})")
    else:
        lines.append(f"   Aerobic final stage: wrist HR not usable ({int(r.peak_valid_windows)} valid windows) → verify with chest strap / RPE")
    lines.append(f"   Usable wrist HR: stress {r.hr_valid_stress:.0%} · aerobic {r.hr_valid_aerobic:.0%} · anaerobic {r.hr_valid_anaerobic:.0%}"
                 if pd.notna(r.hr_valid_aerobic) and pd.notna(r.hr_valid_anaerobic) else f"   Usable wrist HR: stress {r.hr_valid_stress:.0%}")
    print("\\n".join(lines) + "\\n")

for sid in ["S16", "S03", "S04", "f13"]:
    card(sid)
""")
md("""
Four people, four different stories. S16 responds only through the heart, S03 only through the sweat glands, S04
through both while reporting **no** change in perceived stress. f13 reports the largest rise in perceived stress of the
whole sample (+7 points) while heart rate *falls*. Self-report and physiology are complementary, not interchangeable.
""")

md("""
## 8 · Use it with your own clients

The method needs only three numbers, so it transfers to any wearable or test (resting HR, HRV, jump height, a
questionnaire score):

1. **Typical error** of your measurement: measure several clients twice under the same conditions (two rest days, two
   baseline tests) and use `typical_error`. Or borrow a published TE for the same device and protocol.
2. **Smallest worthwhile change**: 0.2 × the between-person SD, or a clinically meaningful threshold if one exists.
3. The client's **observed change**.

The numbers below are **hypothetical**, only to show the calls.
""")
code("""
def judge(change, te, swc, n_tests=1):
    \"\"\"Classify one client's change (average of n_tests) against the SWC with a 90% interval.\"\"\"
    half = I.Z90 * np.sqrt(2) * te / np.sqrt(n_tests)
    low, high = change - half, change + half
    verdict = "clear response" if low > swc else "no meaningful response" if high < swc else "unclear"
    out = f"change {change:+.1f} · 90% interval {low:+.1f} to {high:+.1f} · SWC {swc:.1f} → {verdict}"
    if verdict == "unclear":
        need = int(np.ceil((I.Z90 * np.sqrt(2) * te / swc) ** 2))
        out += f": measure again (about {need} averaged tests make the interval narrower than the SWC)"
    return out

# Hypothetical: resting HR (bpm) of 8 clients measured on two mornings
day1 = np.array([58, 64, 71, 55, 62, 68, 60, 74])
day2 = np.array([61, 62, 74, 57, 60, 71, 63, 72])
te_own = I.typical_error(day1, day2)["te"]
swc_own = I.smallest_worthwhile_change((day1 + day2) / 2)
print(f"your typical error = {te_own:.1f} bpm · your SWC = {swc_own:.1f} bpm")
print(judge(+4.0, te_own, swc_own))                 # one test
print(judge(+4.0, te_own, swc_own, n_tests=6))      # same change, averaged over 6 tests
print()
print("With this dataset's stress-test values (E4, seated):")
print(judge(+6.0, noise.loc["hr_mean", "te"], noise.loc["hr_mean", "swc"]))
""")

md("""
## Take-home for practitioners

1. **The average describes almost nobody.** True individual differences are large (HR: SD 7.6 bpm around +5 bpm).
2. **One short test cannot label a person.** Noise ≈ smallest worthwhile change; ~6 repeats for heart rate.
3. **Watch more than one channel.** Heart and sweat responders are different people; self-report does not tell you which.
4. **External load ≠ internal load.** The same protocol: 46–91% of predicted HRmax.
5. **Check whether the wearable can measure the person before interpreting the person.** Final-stage wrist HR was usable
   in fewer than half of the cyclists.

*Limitations:* healthy adults aged 18–31, one device, single sessions, no ECG or VO₂ reference. Categories describe one
session, not a trait. No clinical inference.

A one-page practitioner guide (English and Spanish) is in the repository: `docs/practitioner_guide.md`,
`docs/guia_profesional.md`.
""")

nb = nbf.v4.new_notebook(); nb.cells = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, sys.argv[1]); print("ok")
