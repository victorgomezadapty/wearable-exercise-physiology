# Final Report: Wearable Physiological Responses to Aerobic Exercise, Anaerobic Exercise and Acute Stress

Data: PhysioNet *Wearable Device Dataset from Induced Stress and Structured Exercise Sessions* v1.0.1 (Empatica E4;
Hongn et al., *Scientific Data* 2025). Full evidence is in notebooks `01`–`07`. All numbers are participant-level
unless stated otherwise. CIs are bootstrap 95% intervals over participants.

---

## Main question: how do wearable signals differ between aerobic exercise, anaerobic exercise and acute stress?

| Signal | Acute stress (TMCT, seated) | Aerobic cycling | Anaerobic sprints |
|---|---|---|---|
| **Heart rate** vs seated rest | **+5.0 bpm** (2.2–7.8), same day | +19 bpm moderate, **+49 bpm** at peak | unmeasurable during the sprint; **+40 bpm** in the 2 min after |
| **EDA tonic level** | ×1.6 | ×2.3 moderate, **×11** at peak | ×3.4 sprint, ×4.5 after |
| **SCR rate** | +0.9 / min | +3.0 to +4.7 / min | +4.8 / min |
| **Skin temperature slope** | no reliable change | no rise; falls within most participants | ≈ −0.1 to −0.2 °C after sprints (event-locked) |
| **Wrist movement** | **decreases** (−0.006 g) | rises with cadence | large bursts, then unloaded pedalling |
| **HRV (RMSSD)** | ≈ −7 ms (suggestive, n = 17–23) | not measurable from wrist PPG | not measurable |

Stress and exercise both activate cardiovascular and sudomotor responses. **Exercise produces responses roughly an
order of magnitude larger, together with movement. Stress produces a real response while the wrist is stiller than
at rest.** At the session level, the two exercise types look similar in HR, EDA and temperature. They differ in the
time course: a steady progressive rise versus bursts followed by recovery.

## Secondary questions

**1 · How does the heart-rate response differ between conditions?**
- Stress: HR rises within ~60 s of task onset, plateaus at +6–7 bpm, and returns as the task ends. During recovery it
  falls *below* the initial baseline (−4.3 bpm), so the baseline probably held anticipatory arousal.
- Aerobic: a staircase that follows workload (median per-participant ρ = 0.95 with stage on quality-valid data).
- Anaerobic: HR keeps rising after the sprint ends and peaks during the first minute of cooldown. Wrist PPG yields
  valid HR in only 3% of sprint windows, so the post-sprint curve rests on 5–15 participants.
- Robustness: the stress response is the same in both cohorts (V1 +5.4, V2 +4.6 bpm). It is hidden by unfiltered E4 HR
  (+2.2 bpm, CI crossing zero) and revealed by quality filtering.

**2 · How do HRV and EDA differ between stress and exercise?**
- EDA rises in both, but on different scales (×1.6 vs ×11) and with different shapes: phasic bursts during a short
  stressor; slow, then steep, thermoregulatory sweating during incremental exercise (flat until ~95 rpm). **EDA level
  alone cannot tell stress from exercise.**
- HRV can only be estimated while seated. RMSSD fell by ~7 ms during the stress task, consistent with vagal withdrawal,
  but this is not significant after multiplicity correction (17–23 participants with enough clean beats). Mean NN
  shortened by 76 ms (p = 0.005).

**3 · Do combinations of signals distinguish states better than single signals?**
Yes. In leave-one-subject-out classification, all signals reach macro-F1 **0.66** (0.61–0.71). The best single modality
(movement) reaches 0.58, HR 0.44, EDA 0.38, and skin temperature 0.35 (chance = 0.33). At the participant level, HR and
EDA responses to stress are unrelated (ρ ≈ 0). Different people respond through different channels, which is another
reason to combine them.

**4 · Which features carry the most information?**
- Three-class problem: **movement intensity**, by far. A large part of the apparent HR contribution is a
  **sensor-failure shortcut**: movement plus a binary "HR missing" flag gives 0.64 of the 0.66. The PPG fails during
  sprints, and the model uses that.
- Where movement cannot help (**stress vs seated rest**), physiology alone reaches macro-F1 **0.65** (0.60–0.70), with
  **EDA** as the most informative single signal (0.61).
- Skin temperature is the least informative signal throughout (ICC ≈ 0–0.3, no reliable effects).

## Other findings worth knowing

- **Leakage:** the same random forest scores 0.83 with random window splits and 0.66 on unseen participants. HR and EDA
  are highly individual (ICC 0.83–0.99 in most states).
- **Self-report vs physiology:** within each person, HR tracks perceived stress (r_rm = 0.40) and EDA does so weakly (0.18).
- **Protocol fidelity:** the wrist accelerometer confirms the prescribed cadence from 85 rpm upward. At 60–75 rpm,
  participants pedalled 7–9 rpm faster than the metronome.
- **No resting baseline in any exercise session.** The seated reference comes from the stress day.
- **25 data issues** catalogued, 15 of them not in the authors' constraint file (`src/data/issues.py`).

## Limitations

Small sample of healthy young adults; cohort confounded with sex, age, training status, setting and protocol version.
No ECG, power, VO₂ or lactate reference, so "aerobic" and "anaerobic" are protocol labels. Wrist PPG is unreliable
during cycling and fails during sprints. Exercise-vs-rest contrasts compare different days. Stress tasks are short.
Empatica HR and IBI come from proprietary algorithms. Results do not generalise to clinical populations or diagnosis.

## Take-home message

> I can work with multimodal wearable data, understand the exercise physiology behind it, process each signal
> appropriately, analyse individual responses, and apply data science without losing sight of what the data mean
> biologically, including when the honest answer is "this is mostly movement and sensor failure, not physiology".
