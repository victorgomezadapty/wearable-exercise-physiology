# Practitioner Guide: What a Wrist Wearable Can and Cannot Tell You About Your Client

For physiotherapists, coaches and personal trainers who use wrist wearables (smartwatches, research bands) with clients.
Every row is backed by an analysis in this repository: notebooks 02, 06, 07 and 08. Spanish version:
[guia_profesional.md](guia_profesional.md).

> Evidence base: 36 healthy young adults, Empatica E4 on the wrist, one session per condition (PhysioNet dataset,
> Hongn et al. 2025). Consumer watches use different algorithms, but they face the same physics: optical heart rate
> at the wrist and movement. Treat this as a guide to questions worth asking, not as clinical guidance.

## Can I trust the number?

| Situation | Trust it? | Evidence from this project | What to do instead |
|---|---|---|---|
| **Heart rate, sitting still** | ✅ Mostly | Valid in ~60–70% of 30-s windows | Use it, and check for gaps |
| **Heart rate, steady cycling** | ⚠️ Often not | Valid in 43% of windows. At the final stage, usable in **14 of 30** people. "Valid-looking" values can be lower than at easier stages | Chest strap for intensity decisions; cross-check with RPE |
| **Heart rate, sprints / intervals** | ❌ No | Valid in **3%** of sprint windows; 12% in the 2 min after | Chest strap, or judge by recovery once still |
| **HRV (RMSSD)** | Seated only | During exercise E4 RMSSD stays at 25–35 ms at ~130 bpm: artefact | Measure HRV seated or lying, still, with ≥ 60 clean consecutive beats |
| **EDA (skin conductance) as a stress marker** | Context-dependent | Stress ×1.6; peak exercise **×11** (sweating) | Only interpret it at rest, and against the person's own baseline |
| **Skin temperature** | ❌ Not informative | No reliable change in any condition; ICC ≈ 0–0.3 | Ignore for decisions |
| **Movement / cadence** | ✅ Yes | Matches the prescribed cadence from 85 rpm; shows stillness under stress | Use it as context for every other signal |

## Can I make a decision about this person?

| Question | Short answer | Evidence | Practical rule |
|---|---|---|---|
| **Is this client a "stress responder"?** | Not from one test | Measurement noise (typical error 2.4 bpm) ≈ smallest worthwhile change (2.3 bpm). After one 3–4 min stress task, **19 of 34** people are unclear on HR | Repeat the measurement (~**6 times** for HR, ~4 for EDA) and compare against the person's own baseline |
| **Do people really respond differently?** | Yes, a lot | True individual-response SD **7.6 bpm** around a mean of +5 bpm. About 1 in 4 has no true HR rise | Never apply the group average to an individual |
| **Which signal should I monitor?** | More than one | HR and EDA responses are unrelated (ρ ≈ −0.06). Of 15 clear responders, only 3 respond on both | Monitoring one channel misses about half of the responders |
| **Does what they *say* match their physiology?** | Partly | Within a person, HR tracks perceived stress moderately (r_rm = 0.40). Self-report does not predict *which* channel responds; one participant responded clearly on both while reporting no change | Ask *and* measure; one does not replace the other |
| **Did the session hit the intended intensity?** | Check individually | The same cadence protocol ended at **46–91% of predicted HRmax** (light to vigorous) in the 14 people who could be measured | Prescribe by internal load (HR zones from a measured max, RPE), not by external load alone |
| **Can I use 220 − age or 208 − 0.7 × age?** | With caution | Individual error ≈ ±10 bpm (≈ ±5 percentage points) | Use a measured HRmax when decisions depend on it |
| **Should I trust a model that "detects stress"?** | Ask how it was validated | The same model scores macro-F1 **0.83** when tested on windows from known people and **0.66** on new people | Only trust results validated on people the model has never seen |

## Five rules

1. **Check whether the wearable can measure the person before interpreting the person.** Look at the gaps and the
   activity context first.
2. **Compare people with themselves.** Baselines differ so much between people (ICC 0.83–0.99) that population thresholds
   mislead.
3. **One measurement is a hypothesis, not a diagnosis.** Use repeated measurements before labelling anyone.
4. **External load is not internal load.** Verify intensity for each person.
5. **Movement explains a lot.** Many "physiological" differences between activities are movement, or a sensor failing
   during movement.

## Limits

Healthy adults aged 18–31, one device, single sessions, no ECG or VO₂ reference. This does not apply to clinical
populations, medications that affect heart rate (e.g. beta-blockers), or diagnosis.
