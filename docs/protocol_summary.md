# Protocol Summary

Sources: Hongn et al., *Scientific Data* 12 (2025), [10.1038/s41597-025-04845-9](https://doi.org/10.1038/s41597-025-04845-9);
the protocol diagrams embedded in the authors' `Wearable_Dataset.ipynb`; and **verification against every tag file**
(this project, notebook 01 §6). Observed durations are tag-to-tag medians (range) in seconds.

> Rule for all later phases: **cut windows from the tags, never from nominal durations.**
> Observed durations deviate from the plan, sometimes by minutes.

## 0. Study design at a glance

| | Cohort V1 (`S01`–`S18`) | Cohort V2 (`f01`–`f18`) |
|---|---|---|
| Participants | 18 men, 18–22 y, 17/18 train regularly | 17 women + 1 man, 21–31 y, 4/13 train regularly |
| Setting | Individual sessions in a lab | Stress: **remote**. Exercise: **group spinning classes** |
| Stress | 18 sessions, protocol V1 | 18 participants (19 sessions), protocol V2 |
| Aerobic | 17 (S12 did not do it) | 13 (f14–f18 did not do exercise) |
| Anaerobic | 18 | 13 |
| Days | Stress, aerobic and anaerobic on **different days** (no carry-over, but day-to-day variability) | same |

Cohort, sex and protocol version vary together, so a V1-vs-V2 difference cannot be attributed to any one of them.
Device: Empatica E4 on the non-dominant wrist. Exclusion criteria: chronic illness, family history of sudden
death during exercise, psychiatric treatment, medication affecting physiology.

---

## 1. Acute-stress protocol

Seated, earphones, researcher absent during rests. Self-reported stress (SL) is given verbally before and
after each block.

### Stress V1: 13 tags (authors' diagram shows 12)

| Boundary (tags) | Segment | Phase | Nominal | Observed median (range) |
|---|---|---|---|---|
| start → 1 | pre_baseline | transition | – | 177 (1–371) |
| 1 → 2 | **baseline** | baseline | 180 | 190 (163–247) |
| 2 → 3 | sl_report_1 | transition | – | 103 (71–175) |
| 3 → 4 | **stroop** (colour-word interference) | stress | 120 | 109 (92–152) |
| 4 → 5 | **first_rest** | rest | 300 | 326 (232–440) |
| 5 → 6 | **tmct** (Trier Mental Challenge: timed arithmetic + aversive noise, answers aloud) | stress | 180 | 137 (125–169) |
| 6 → 7 | **second_rest** | rest | 300 | 308 (227–369) |
| 7 → 8 | **real_opinion** (controversial topic) | stress | 30 | 32 (28–35) |
| 8 → 9 | sl_report_2 | transition | – | 34 |
| 9 → 10 | **opposite_opinion** (defend the opposite view) | stress | 30 | 31 (27–37) |
| 10 → 11 | sl_report_3 | transition | – | 31 |
| 11 → 12 | **subtract** (1022 − 13 serially, aloud) | stress | 30 | 32 (31–34) |
| 12 → 13 | sl_report_4 | transition | – | 34 (12–44) |
| 13 → end | post | transition | – | 37 (S02: 1,800 = duplicated data) |

**Finding:** all 18 V1 files contain 13 tags. The 30-s tasks fall exactly on tags 7–8, 9–10 and 11–12, which
confirms that tags 1–12 follow the diagram (and the authors' notebook code). Tag 13 is an extra closing press.

### Stress V2: 9 tags (remote; Stroop removed; longer rests with a relaxing video)

| Boundary | Segment | Phase | Nominal | Observed median (range) |
|---|---|---|---|---|
| start → 1 | **baseline** | baseline | not specified | 784 (142–2,337) |
| 1 → 2 | sl_report_1 | transition | – | 94 |
| 2 → 3 | **tmct** | stress | 180 | 261 (217–452) |
| 3 → 4 | **first_rest** | rest | 600 | 853 (778–1,086) |
| 4 → 5 | **real_opinion** | stress | 30 | 38 (29–45) |
| 5 → 6 | sl_report_2 | transition | – | 26 |
| 6 → 7 | **opposite_opinion** | stress | 30 | 38 (30–48) |
| 7 → 8 | **second_rest** (moved before the subtraction task) | rest | 600 | 807 (439–1,169) |
| 8 → 9 | **subtract** | stress | 30 | 38 (26–65) |
| 9 → end | post | transition | – | 325 |

Physiology notes:
- The 30-s tasks are short relative to EDA (seconds-scale onset, slow recovery) and HR-smoothing (10-s window)
  dynamics. Responses will carry over into the following report period, and successive tasks are not independent.
- In V2 the baseline is the long pre-protocol period. In V1 it is a defined 3-min block. Rest blocks may still
  contain recovery from the previous task. The authors used only the second half of each rest.

---

## 2. Aerobic protocol (stationary bike; adapted from the Storer-Davis maximal test)

Cadence is set by a metronome: one beat per foot-down, so 2 beats per revolution. Resistance is a percentage of
each participant's individually determined maximum. **Absolute power (W) was not recorded.**

### Aerobic V1: 12 tags (individual sessions, ~35 min)

| Boundary | Segment | Resistance (paper) | Nominal | Observed median (range) |
|---|---|---|---|---|
| start → 1 | **warmup**, unloaded pedalling | 0 | 180 | 180 (172–219) |
| 1 → 2 | rpm_60 | 20% | 180 | 182 |
| 2 → 3 | rpm_70 | ↑ | 180 | 176 |
| 3 → 4 | rpm_75 | 30% | 180 | 182 |
| 4 → 5 | rpm_80 | 35% | 180 | 182 |
| 5 → 6 | rpm_85 | 40% | 180 | 179 |
| 6 → 7 | rpm_90 | 45% | 120 | 119 |
| 7 → 8 | rpm_95 | 50% | 120 | 119 |
| 8 → 9 | rpm_100 | 50% | 120 | 120 |
| 9 → 10 | rpm_105 | 50% | 120 | 119 |
| 10 → 11 | rpm_110 | 50% | 120 | 121 |
| 11 → 12 | **cooldown**, unloaded | 0 | 240 | 238 |
| 12 → end | **rest**, seated still | – | 120 | 120 (94–195) |

- The authors' diagram shows 90 rpm as 3:00. The paper text says 2:00, and the data confirm **2:00**.
- **There is no seated resting baseline.** The recording starts with unloaded pedalling. "Resting HR" cannot be
  measured in V1 exercise sessions. The closest reference is the warm-up, or the stress-day baseline (a different day).

### Aerobic V2: 8 tags (group spinning classes)

| Boundary | Segment | Nominal | Observed median (range) |
|---|---|---|---|
| start → 1 | **baseline_warmup** (4:30 baseline + 2:15 warm-up, **no tag between them**) | 405 | 708 (125–1,592) |
| 1 → 2 | rpm_70 | 90 | 119 |
| 2 → 3 | rpm_75 | 90 | 113 |
| 3 → 4 | rpm_80 | 90 | 120 |
| 4 → 5 | rpm_85 | 675 | 717 (615–890) |
| 5 → 6 | rpm_90_95 (90 or 95 rpm depending on the participant) | 270 | 176 (9–415) |
| 6 → 7 | cooldown | 180 | 214 |
| 7 → 8 | rest, seated on the bike | 120 | 120 |
| 8 → end | post | – | 88 |

**Group sessions** (identified from clustered de-identified start times; the tag timing differs systematically between groups):

| Group | Participants | Characteristic |
|---|---|---|
| A | f05, f06, f07 | **90/95-rpm stage absent**: tags 5 and 6 pressed 9–15 s apart (out of order in f07); 85 rpm held 11.5–15 min |
| B | f04, f09, f10 | 90/95 rpm held ~7 min; cooldown ~2 min |
| C | f01, f03, f12 | close to nominal (90/95 ≈ 3 min) |
| D | f02, f11, f13 | close to nominal |
| E | f08 | alone; close to nominal |

The separation between baseline and warm-up is not tagged in V2. A seated baseline would have to be found from
the movement signal (ACC). That is a Phase 2 task.

---

## 3. Anaerobic protocol (stationary bike; adapted from the Wingate test)

### Anaerobic V1: 7 tags

| Boundary | Segment | Nominal | Observed median (range) |
|---|---|---|---|
| start → 1 | **warmup**, unloaded | 180 | 182 (175–250) |
| 1 → 2 | **sprint_1**, all-out, high resistance | 30 | 32 (29–42) |
| 2 → 3 | cooldown_1, unloaded | 240 | 251 |
| 3 → 4 | **sprint_2** | 30 | 32 |
| 4 → 5 | cooldown_2 | 240 | 245 |
| 5 → 6 | **sprint_3** | 30 | 31 |
| 6 → 7 | cooldown_3 | 240 | 248 |
| 7 → end | **rest**, seated still | 120 | 123 |

No seated baseline (same caveat as Aerobic V1).

### Anaerobic V2: 11 tags (group sessions)

| Boundary | Segment | Nominal | Observed median (range) |
|---|---|---|---|
| start → 1 | **baseline** | 270 | 711 (1–1,446) |
| 1 → 2 | warmup | 270 | 200 (88–243) |
| 2 → 3 | **sprint_1** | 45 | 36 (28–45) |
| 3 → 4 | cooldown_1 | 255 | 203 |
| 4 → 5 | **sprint_2** | 45 | 35 |
| 5 → 6 | cooldown_2 | 225 | 197 |
| 6 → 7 | **sprint_3** | 45 | 31 |
| 7 → 8 | cooldown_3 | 225 | 192 |
| 8 → 9 | **sprint_4** | 45 | 33 |
| 9 → 10 | cooldown_4 | 225 | 196 |
| 10 → 11 | rest | 120 | 146 |
| 11 → end | post | – | 284 |

- The planned 45-s sprints last a median **31–36 s** tag-to-tag. Cooldowns are shorter than planned.
- `f04`: first tag at 1 s, so **no baseline** was recorded.

---

## 4. Sessions requiring manual segment maps

| Session | Tags | Interpretation |
|---|---|---|
| AEROBIC/S03 | 7 | warm-up, 60–85 rpm, cooldown (240 s), rest. The constraint file says 90 rpm was reached; if so, it was untagged and sits inside "cooldown" |
| AEROBIC/S07 | 9 | warm-up, 60–95 rpm, cooldown, rest (consistent with the constraint file) |
| AEROBIC/S11_a | 10 | warm-up, 60–105 rpm, then ~64 s of 110 rpm before connection loss |
| AEROBIC/S11_b | 1 | **Ambiguous.** Starts 3.7 min after S11_a. Movement before the tag is low (cooldown-like) and near-still after it. The constraint file says it holds the 110-rpm block |
| ANAEROBIC/S06 | 5 | warm-up, 2 sprints + cooldowns, rest (3rd sprint missing) |
| ANAEROBIC/S16_a | 4 | warm-up, sprint 1, cooldown, sprint 2, partial cooldown |
| ANAEROBIC/S16_b | 5 | ~46 s unknown, sprint 3, cooldown, **sprint 4**, cooldown, rest. S16 did four sprints in a three-sprint protocol |
| STRESS/f14_a | 0 | baseline only (703 s) |
| STRESS/f14_b | 9 | segment before tag 1 = end of baseline; otherwise the V2 map |
| AEROBIC/f07 | 8 | tags 5 and 6 out of order in the file and sorted before mapping |

All mappings are implemented in `src/data/protocol.py` (`PROTOCOLS`, `MANUAL_MAPS`). All 100 sessions are
segmented, yielding 1,064 segments (`data/interim/segments.csv`).

---

## 5. Implications for comparing conditions

1. **Exercise intensity is relative, not absolute.** Resistance is a percentage of an individually determined
   maximum, and power was not measured. Between-person comparisons of "the same stage" are approximate.
2. **Aerobic vs anaerobic is not a pure intensity contrast.** The anaerobic protocol alternates 30–45-s all-out
   efforts with long unloaded recoveries. Most of an anaerobic session is low-intensity pedalling.
3. **Stress vs exercise differs in posture, movement and duration** as well as in physiological state. Any
   classifier can trivially exploit movement. The physiologically interesting question is what HR/EDA/TEMP
   add *beyond* movement.
4. **Reference periods differ by protocol and cohort.** Stress V1: 3-min seated baseline. Stress V2: long
   pre-protocol period. Exercise V1: unloaded pedalling only. Exercise V2: an untagged seated period inside
   `baseline_warmup`.
5. **Group sessions in V2 exercise** are a shared-context cluster (same instructor timing, room, social setting).
