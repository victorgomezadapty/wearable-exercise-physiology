# Physiological Interpretation

In Phase 1, before any group-level results were computed, the **expected** physiology was written down so that the
findings could be compared with prior expectations rather than rationalised afterwards. This document closes that
loop.

## Expected vs observed

| Signal / condition | Expected (Phase 1) | Observed | Verdict |
|---|---|---|---|
| HR, acute stress | modest rise, +5–20 bpm | **+5.0 bpm** (2.2–7.8); returns, then undershoots in recovery | ✅ at the low end |
| HR, aerobic | near-linear rise with workload | staircase, ρ = 0.95 with stage; +49 bpm at peak | ✅ |
| HR, anaerobic | steep rise peaking *after* the sprint, upward drift | rise continues after the sprint, peak in the first minute of cooldown | ✅ but measurable in only 5–15 participants |
| HRV, stress | RMSSD decreases | ≈ −7 ms, not significant after Holm (n = 17–23) | ↔ direction as expected, underpowered |
| HRV, exercise | unmeasurable from wrist PPG | E4 RMSSD of 25–35 ms at HR ~130 bpm is artefact | ✅ (correctly excluded) |
| EDA, stress | phasic bursts, small tonic rise | ×1.6 tonic, +0.9 SCR/min, returns in recovery | ✅ |
| EDA, aerobic | slow tonic rise to tens of µS | flat until ~95 rpm, then steep: **a sweating threshold** | ✅ plus a non-linearity |
| Skin temp, stress | small drop (vasoconstriction) | no reliable change | ❌ not detected |
| Skin temp, aerobic | early drop, later rise | flat at group level, falling within most participants | ↔ drop yes, rise no |
| ACC, stress | ≈ no movement | **less** movement than at rest | ✅ plus a stillness effect |
| ACC, aerobic | rhythm ≈ 2 × cadence | confirmed; cadence matches prescription from 85 rpm | ✅ |

## Interpretation

**Psychological stress is a small but real autonomic response.** About +5 bpm and a 1.6-fold rise in skin conductance
during a demanding arithmetic task, while participants sat *more* still than at rest. The fall of HR below baseline
during recovery shows that the "resting" baseline already contained anticipatory arousal. This is a familiar problem
in laboratory stress protocols, and it means the true task response is probably closer to the TMCT-vs-recovery
difference (−9 bpm).

**Exercise dominates every channel.** At the aerobic peak, HR rises by ~10 times the stress response and EDA by ~11-fold,
driven by metabolic demand and thermoregulatory sweating. EDA's non-linear rise (flat, then steep from ~95 rpm) fits
the delayed onset of sweating once heat production accumulates. Skin temperature at the wrist does not rise. Cutaneous
vasoconstriction during exercise and evaporative/convective cooling at the exposed wrist outweigh heat dissipation.

**Aerobic and anaerobic exercise are hard to separate from the wrist.** Averaged over a session, their HR, EDA and
temperature are similar. Their difference is temporal: steady progression versus bursts with recoveries. And the most
discriminating physiological signal for sprints, HR, is exactly the one the wrist PPG cannot measure during the effort.

**Individuality is the norm.** HR and EDA set points differ so much between people (ICC 0.83–0.99) that population
thresholds are unreliable. Stress responders on HR are not the same people as responders on EDA (ρ ≈ 0). The
multimodal view matters for individual interpretation, not just for classifiers.

## Cautions that shaped the conclusions

- EDA is not specific to psychological stress. Its *magnitude and context* separate stress from exercise, not its
  presence.
- HR is not specific to exercise: stress raises it without movement.
- Feature importance is not mechanism. The classifier's reliance on "HR missing" during sprints is a property of the
  sensor, not of physiology (notebook 07 §5b).
- Exercise-vs-rest differences span two days. Stress-vs-rest differences are same-day and are the most trustworthy.
- No clinical inference: healthy young adults, single sessions, a research wearable without reference measurements.
