import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from nbkit import NB, SETUP

nb = NB()
nb.md("""
# 03 · Protocol Segmentation and Analysis States

Phase 1 mapped every tag to a protocol segment (`src/data/protocol.py`). This notebook checks whether participants
actually did what the protocol prescribed, identifies valid reference periods, and defines **analysis states that are
comparable across the two protocol versions**. These states are used in every later notebook.
""")
nb.code(SETUP + '''
w = pd.read_csv(PROCESSED / "windows.csv")
seg = pd.read_csv(INTERIM / "segments.csv")
print(f"{len(seg):,} segments · {len(w):,} windows")
''')

nb.md("""
## 1 · Did participants pedal at the prescribed cadence?

The wrist oscillates once per foot-down, so cadence ≈ ACC dominant frequency / 2. Per-window estimates are noisy
because movement at the wrist is small with the hands on the handlebars. Each participant's median per stage is
shown, then the median across participants.
""")
nb.code('''
a = w[(w.condition == "AEROBIC") & w.segment.str.match(r"rpm_\\d+$") & w.acc_valid].copy()
a["rpm"] = a.segment.str[4:].astype(int)
a["cadence_acc"] = a.acc_dom_freq_per_min / 2
per = a.groupby(["cohort", "subject_id", "rpm"]).cadence_acc.median().reset_index()
fig, ax = plt.subplots(figsize=(7.5, 5))
for coh, mk in [("V1", "o"), ("V2", "s")]:
    d = per[per.cohort == coh]
    ax.scatter(d.rpm + (0.8 if coh == "V2" else -0.8), d.cadence_acc, s=14, color=C["AEROBIC"], alpha=0.3, marker=mk, lw=0)
    med = d.groupby("rpm").cadence_acc.median()
    ax.plot(med.index, med.values, marker=mk, color=P.TEXT if coh == "V1" else P.TEXT_2, lw=2, label=f"median, cohort {coh}")
ax.plot([55, 115], [55, 115], color=C["AEROBIC"], lw=1, label="prescribed = measured")
ax.set_xlabel("prescribed cadence (rpm)"); ax.set_ylabel("cadence estimated from wrist ACC (rpm)")
ax.set_xlim(55, 115); ax.set_ylim(40, 140); ax.legend(loc="upper left")
ax.set_title("Protocol fidelity: prescribed vs measured cadence", loc="left")
P.save(fig, "03_cadence_fidelity"); plt.show()
per.groupby(["cohort", "rpm"]).cadence_acc.median().unstack(0).round(1)
''')
nb.md("""
From 85 rpm upward, the measured cadence is within ~2–6 rpm of the prescription (cohort V1 medians: 83, 88, 92,
99, 101, 104 rpm for 85–110). At 60–75 rpm participants pedalled **7–9 rpm faster than the metronome** (68, 77,
82 rpm), because a very slow cadence feels unnatural on a spinning bike. So the early stages were less different
from each other than intended, and workload progression came mostly from resistance and the higher-cadence stages.
The wrist accelerometer independently confirms that the protocol was followed.
""")

nb.md("""
## 2 · Is there a resting reference in the exercise sessions?

Candidate reference periods, compared on wrist movement (SD of |ACC| over 1 s; seated still ≈ 0.007 g):
""")
nb.code('''
cand = {
    "Stress day: seated baseline": w[w.state == "SEATED_BASELINE"],
    "Stress day: seated rests": w[w.state == "SEATED_REST"],
    "Anaerobic V2: tagged 'baseline'": w[w.state == "PRE_EXERCISE_BASELINE"],
    "Aerobic V2: 'baseline + warm-up'": w[(w.condition == "AEROBIC") & (w.segment == "baseline_warmup")],
    "Exercise V1: warm-up (unloaded)": w[(w.cohort == "V1") & (w.condition != "STRESS") & (w.segment == "warmup")],
    "Post-exercise seated rest": w[w.state == "POST_EXERCISE_REST"],
}
fig, ax = plt.subplots(figsize=(10, 3.8))
for i, (name, d) in enumerate(cand.items()):
    v = d.acc_movement.dropna()
    ax.boxplot(v.clip(upper=0.25), positions=[i], vert=False, widths=0.5, showfliers=False,
               medianprops=dict(color=P.TEXT, lw=2), boxprops=dict(color=P.TEXT_2), whiskerprops=dict(color=P.TEXT_2), capprops=dict(color=P.TEXT_2))
    ax.text(0.255, i, f"median {v.median():.3f} g", va="center", fontsize=8, color=P.TEXT_2)
ax.set_yticks(range(len(cand)), list(cand)); ax.invert_yaxis(); ax.set_xlim(0, 0.31)
ax.set_xlabel("wrist movement (g)"); ax.grid(axis="y", visible=False)
ax.set_title("Only the stress-day seated periods are actually still", loc="left")
P.save(fig, "03_reference_periods"); plt.show()
''')
nb.md("""
The V2 exercise "baselines" happened in a group spinning room. Wrist movement there is ~6× higher than seated
stillness, about the same as pedalling. Participants were adjusting bikes, talking and moving. The V1 exercise sessions
start directly with unloaded pedalling. **No exercise session contains a usable resting baseline.**

**Decision:** the resting reference for every participant is the **seated baseline of the stress day**. It is
recorded on a different day, so day-to-day variability is part of any "change from rest". This is stated wherever it
is used. The 30 participants with all three protocols have this reference. f14–f18 have stress data only.
""")

nb.md("""
## 3 · Ambiguous sessions

- **AEROBIC/S03**: the data-constraints file says the participant "reached 90 rpm". The last tagged stage shows a
  wrist rhythm of 86–90 rpm. The following 240-s block has low, irregular movement (no rhythmic pedalling), so it is a
  genuine cooldown. Labels unchanged.
- **AEROBIC/S11_b**: movement before its only tag is cooldown-like, not 110-rpm pedalling. It is **excluded** from all
  analyses (state = none).
""")
nb.code('''
s3 = w[(w.condition == "AEROBIC") & (w.session_id == "S03") & w.segment.isin(["rpm_85", "cooldown"])]
s3.groupby("segment")[["acc_movement", "acc_periodicity", "acc_dom_freq_per_min"]].median().round(3)
''')

nb.md("""
## 4 · Analysis states, comparable across protocol versions

| Analysis state | Definition | Why |
|---|---|---|
| `REST_SEATED` | stress-day seated baseline | only true resting reference |
| `STRESS_RECOVERY` | second half of each seated rest | avoids carry-over from the preceding task (as the authors did) |
| `STRESS_TMCT` | Trier Mental Challenge Test | the main stressor; present in both versions |
| `STRESS_SHORT` | opinion, opposite opinion, subtraction (30 s each), Stroop (V1) | short tasks, analysed separately |
| `AEROBIC_MODERATE` | 70, 75, 80 rpm, plus the first 3 min of 85 rpm | stages shared by V1 and V2 with similar exposure time |
| `AEROBIC_PEAK` | last 2 min of the final completed stage | highest workload each person reached |
| `SPRINT` | all-out sprints | movement and EDA only; HR unmeasurable (notebook 02) |
| `POST_SPRINT` | first 2 min of the cooldown after each sprint | the only window where the anaerobic HR response is measurable |
| `POST_EXERCISE_REST` | seated rest after exercise | recovery |
""")
nb.code('''
def analysis_state(r):
    if r.condition == "AEROBIC" and r.session_id == "S11_b":
        return None
    if r.state == "SEATED_BASELINE":
        return "REST_SEATED"
    if r.state == "SEATED_REST":
        seg_dur = r.seg_duration
        return "STRESS_RECOVERY" if r.t_in_segment_s >= seg_dur / 2 else None
    if r.state == "STRESS_TASK":
        return "STRESS_TMCT" if r.segment == "tmct" else "STRESS_SHORT"
    if r.state == "AEROBIC_STAGE":
        if r.segment in ("rpm_70", "rpm_75", "rpm_80"):
            return "AEROBIC_MODERATE"
        if r.segment == "rpm_85" and r.t_in_segment_s + 30 <= 180:
            return "AEROBIC_MODERATE"
        return None  # peak assigned below
    if r.state == "SPRINT":
        return "SPRINT"
    if r.condition == "ANAEROBIC" and r.segment.startswith("cooldown") and r.t_in_segment_s + 30 <= 120:
        return "POST_SPRINT"
    if r.state == "POST_EXERCISE_REST":
        return "POST_EXERCISE_REST"
    return None

dur = seg.set_index(["condition", "session_id", "segment"]).duration_s
w["seg_duration"] = [dur.get((c, s, g), np.nan) for c, s, g in zip(w.condition, w.session_id, w.segment)]
w["analysis_state"] = [analysis_state(r) for r in w.itertuples()]

# AEROBIC_PEAK: last 2 min of the final completed exercise segment of each aerobic session
ex = w[(w.condition == "AEROBIC") & (w.phase == "exercise") & (w.session_id != "S11_b")]
for sid, g in ex.groupby("session_id"):
    last_seg = g.loc[g.end_s.idxmax(), "segment"]
    gs = g[g.segment == last_seg]
    peak_idx = gs[gs.end_s >= gs.end_s.max() - 120].index
    w.loc[peak_idx, "analysis_state"] = "AEROBIC_PEAK"

w.to_csv(PROCESSED / "windows.csv", index=False)
STATES = ["REST_SEATED", "STRESS_RECOVERY", "STRESS_TMCT", "STRESS_SHORT", "AEROBIC_MODERATE",
          "AEROBIC_PEAK", "SPRINT", "POST_SPRINT", "POST_EXERCISE_REST"]
summary = (w[w.analysis_state.notna()].groupby("analysis_state")
           .agg(windows=("win_idx", "size"), participants=("subject_id", "nunique"),
                hr_valid=("hr_valid", "mean"), eda_valid=("eda_valid", "mean"))
           .reindex(STATES))
summary
''')
nb.code('''
peak = w[w.analysis_state == "AEROBIC_PEAK"].groupby(["cohort", "session_id"]).segment.first()
print("Final completed stage used as AEROBIC_PEAK:")
print(peak.groupby("cohort").value_counts().to_string())
''')
nb.md("""
`AEROBIC_PEAK` is not the same workload for everyone. V1 mostly reached 110 rpm at 50% of maximum resistance. V2
reached 90/95 rpm, or stayed at 85 rpm in the group that skipped the last stage. Absolute power is unknown in both
cases. Peak comparisons are therefore within cohort, or framed as each person's highest *protocol* stage.
""")
nb.save(sys.argv[1])
print("ok")
