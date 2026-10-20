# Phase 1 Report: Data Understanding

*Status: complete. No preprocessing, feature engineering or modelling has been done.*
Evidence for every statement: [`notebooks/01_data_understanding.ipynb`](../notebooks/01_data_understanding.ipynb).
Detailed references: [`data_dictionary.md`](data_dictionary.md), [`protocol_summary.md`](protocol_summary.md).

---

## 1. Dataset structure

- PhysioNet **v1.0.1** (latest). **707/707 files match the official SHA-256 manifest.**
- `Wearable_Dataset/{STRESS,AEROBIC,ANAEROBIC}/<session>/` × 7 Empatica CSVs (ACC, BVP, EDA, HR, IBI, TEMP, tags).
  Plus metadata: `subject-info.csv`, `Stress_Level_v1/v2.csv`, `data_constraints.txt`, `Data_Dictionary.csv`.
- **100 sessions** (37 stress / 31 aerobic / 32 anaerobic), 217 MB. Three participant-conditions are split into
  `_a`/`_b` files after Bluetooth loss (STRESS f14, AEROBIC S11, ANAEROBIC S16).

## 2. Protocol description

| Condition | V1 (S01–S18, individual lab sessions) | V2 (f01–f18) |
|---|---|---|
| STRESS | baseline 3′ → Stroop → rest 5′ → TMCT → rest 5′ → opinion / opposite opinion / serial subtraction (30″ each) | remote; no Stroop; ~13–14′ rests with video; rest moved before subtraction |
| AEROBIC | warm-up 3′ → 60–110 rpm in 10 stages (2–3′ each, resistance 20 → 50% of individual max) → cooldown 4′ → rest 2′ | group spinning: baseline + warm-up → 70/75/80 rpm → 85 rpm ~12′ → 90/95 rpm → cooldown → rest |
| ANAEROBIC | warm-up 3′ → 3 × (30″ all-out sprint + 4′ unloaded) → rest 2′ | group: baseline → warm-up → 4 × (45″ planned sprint, **~31–36″ observed** + ~3.3′ cooldown) → rest |

Key facts for analysis:
- **V1 exercise sessions have no seated resting baseline.** They start with unloaded pedalling.
- Observed segment durations deviate from nominal ones (e.g. V2 TMCT 4.3′ vs 3′ planned; V1 TMCT 2.3′).
- Absolute power output was **not recorded**. Intensity is only relative (% of individual max resistance, cadence).

## 3. Participant structure

- 36 participants. **30 completed all three protocols** (17 V1 + 13 V2), so the core comparison is **within-subject**.
- f14–f18 have stress data only and no demographics.
- **Cohort = sex = protocol version = setting** (V1: 18 men, 20.3 y, 17/18 train regularly; V2: 17 women + 1 man,
  25.1 y, 4/13 train regularly). V1-vs-V2 differences are not interpretable as sex effects.
- V2 exercise was done in **group classes**. Aerobic V2 ran in five sessions (four groups of three, plus f08
  alone) and anaerobic V2 in six. Tag timing differs systematically between groups.

## 4. Signal inventory

| Signal | What it measures | Origin | Physiological meaning |
|---|---|---|---|
| ACC (x,y,z) | wrist acceleration | raw | **Movement context** (not physiology). On the bike it tracks cadence (dominant frequency ≈ 2 × rpm), not leg power |
| BVP | wrist PPG waveform | raw (Empatica-filtered) | Pulse waveform, the basis for HR/IBI. Unitless; highly motion-sensitive |
| HR | heart rate | **Empatica algorithm** (10-s window) | Cardiovascular load, but see quality issues |
| IBI | beat-to-beat intervals | **Empatica algorithm** | HRV (autonomic balance) when coverage allows |
| EDA | skin conductance | raw | Sympathetic sudomotor activity (psychological arousal **and** thermoregulatory sweating) |
| TEMP | wrist skin temperature | raw | Peripheral vasomotor tone and thermoregulation; strongly affected by contact and airflow |
| tags | button presses | manual | Protocol segmentation |

## 5. Sampling rates (verified in every file header)

**ACC 32 Hz · BVP 64 Hz · EDA 4 Hz · TEMP 4 Hz · HR 1 Hz · IBI event-based (quantised to 1/64 s).**
All 500 uniform-signal headers match the documentation. There are no exceptions. Alignment: common start
timestamp; **HR starts +10 s later**; file ends differ by ≤ 7.5 s.

## 6. Data dictionary

See [`data_dictionary.md`](data_dictionary.md). It covers file formats, units, observed ranges, metadata parsing,
derived tables and the segment vocabulary.

## 7. Signal-quality issues

Issues **documented by the authors** (10): S02-stress duplicated export, f07-stress dock covering the PPG and TEMP
sensors, connection losses (f14, S11, S16), incomplete protocols (S03, S07 aerobic; S06 anaerobic), S12 without
aerobic data, S01-anaerobic empty IBI.

**Found in this phase and not in `data_constraints.txt`** (15, full list in `src/data/issues.py`). The most
consequential:

1. **Empatica HR during cycling is often physiologically implausible.** Across 17 aerobic V1 sessions, the
   rank correlation between workload stage and HR ranges from −0.61 to 1.00. There are flat traces (S15 ≈ 94 bpm
   from 60 to 110 rpm), erratic drops (S01: 120 → 89 bpm between consecutive stages), and correctly ordered but
   implausibly low peaks (S17, S11_a ≈ 100 bpm at the hardest stages). In ~25% of stages, HR or the dominant BVP
   frequency coincides with the pedalling cadence, which is consistent with PPG motion artefact.
2. **Skin-temperature fault codes (207–235 °C)** in 4 sessions (AEROBIC S07 100%, ANAEROBIC S02 92%, S05 62%,
   AEROBIC S09 first 220 s).
3. **Stuck accelerometer axis**: ANAEROBIC f09, z-axis at +127 for 93% of samples.
4. **Absent PPG**: AEROBIC f04, BVP exactly zero for 13.7% of samples and a single detected beat, yet HR.csv is populated.
5. **Tag anomalies**: 13 tags in all Stress V1 files (diagram: 12); empty tag file (STRESS f14_a); out-of-order tags
   (AEROBIC f07); a group whose 90/95-rpm stage is absent (AEROBIC f05–f07); no baseline (ANAEROBIC f04).
6. **IBI integrity**: STRESS S02 has a 1959 start date, an embedded second export header and non-monotonic times.
7. **TEMP behaviour**: a few sessions start cold and need 10–20 min to equilibrate. TEMP becomes noisy during cycling.

Confirmed rather than new: the S02 duplication was located exactly by brute-force search (ACC sample 49,542;
BVP 99,088; EDA/TEMP 6,192). No other session contains a repeated block.

## 8. Missing-data assessment

| What | Extent |
|---|---|
| Missing sessions | AEROBIC S12; exercise for f14–f18 (by design) |
| Missing/empty files | 2 of 700 (ANAEROBIC/S01/IBI.csv, STRESS/f14_a/tags.csv) |
| NaN inside signal files | none |
| **IBI coverage** (Σ IBI / duration) | stress median **58%**; aerobic and anaerobic **19%**; longest gap 23 min. Missingness is **not at random**: it depends on movement, so it differs by condition |
| Demographics | missing for f14–f18 |
| Invalid-by-sensor segments | TEMP (4 sessions with fault codes, f07-stress dock), ACC (f09 anaerobic), BVP/HR/IBI (f07 stress, f04 aerobic) |
| Recording-length differences | Stress V1 median 27 min vs V2 54 min; Anaerobic V1 19 min vs V2 40 min; Aerobic V1 34 min vs V2 43 min. Pre-protocol periods range from 1 s to 39 min |

## 9. Potential analytical questions

Cardiovascular
- How large is the HR response to each stress task relative to a seated baseline, and how does it compare to the
  HR response to moderate cycling *within the same person*?
- HR recovery kinetics after anaerobic sprints vs after aerobic cooldown (time constant, 60-s HRR), restricted to
  segments that pass the HR quality check.
- Can HR be recovered reliably from BVP during cycling with a motion-aware method (e.g. ACC-referenced spectral
  subtraction), validated against the expected monotonic aerobic response?

Autonomic
- RMSSD/SDNN in stress tasks vs rests (seated, best IBI coverage). Is the 30-s task length even sufficient?
- EDA: phasic response rate in stress tasks vs tonic drift in exercise. Do the two conditions differ in *shape*
  (fast phasic bursts vs slow thermoregulatory rise) rather than in level?

Movement vs physiology
- How much HR/EDA variance is explained by movement intensity (ACC) alone, and what remains condition-specific?
- During stress (near-zero movement), is there a physiological response that ACC cannot detect at all?

Individual responses
- Are stress "responders" (by HR/EDA) the same people who report higher stress? (Self-report vs physiology.)
- Within-person vs between-person variability of HR and EDA responses across the three days.

## 10. Limitations of the dataset

- **Small sample** (30 with all conditions) and **two non-exchangeable cohorts** confounded with sex, age, training
  status, protocol version and setting.
- **Wrist PPG during cycling** is unreliable. There is no ECG or chest-strap reference to validate HR or HRV.
- **No absolute workload** (W, VO₂, RPE, lactate). "Aerobic" and "anaerobic" are protocol labels, not verified
  metabolic states.
- **Stress tasks are short** (30″) relative to the dynamics of EDA, HR smoothing and HRV windows.
- **Different days per condition.** Daily state (sleep, caffeine, time of day, ambient temperature) is uncontrolled
  and unrecorded.
- **Protocol deviations** (group timing, early stops, extra sprint) and manual tag presses with 1-s resolution and
  human latency.
- **Empatica-derived HR/IBI are black-box** algorithms with undocumented artefact rejection.
- Healthy young volunteers from one institution. No clinical generalisation; nothing here supports diagnosis.
- Self-reported stress uses a single verbal item. The scale anchors in the file (0 occurs) disagree with the paper (1–10).
- The authors' published classification (93/91/84% accuracy, XGBoost) used 10-fold CV on segments, with no
  indication of participant-grouped splitting. Those figures may be optimistic due to participant leakage, and
  they are not a benchmark this project should try to match.

## 11. Proposed Phase 2: Signal Quality and Protocol Segmentation

Goal: decide **which segments of which signals are trustworthy**, before any physiological comparison.

1. **Segment-level signal-quality index (SQI) per modality** (`02_signal_quality.ipynb`)
   - BVP: spectral SQI (fraction of power near the dominant cardiac frequency), skewness/perfusion indices,
     agreement between BVP-derived and Empatica HR.
   - HR: plausibility rules (range, rate of change), **cadence coincidence** using the prescribed rpm and the ACC
     dominant frequency, and monotonicity plus magnitude across aerobic stages.
   - IBI: per-segment coverage, artefact proportion and minimum beat count for each HRV metric.
   - EDA: contact loss (< 0.05 µS), abrupt jumps (motion), flatlines.
   - TEMP: fault-code masking, equilibration window, contact-noise index.
   - ACC: saturation, stuck axes.
   - Output: `data/interim/segment_quality.csv` with pass/fail and the reason per signal × segment.
2. **Re-derive HR/IBI from BVP** with an open method (e.g. NeuroKit2), compare it with Empatica's output, and keep
   whichever passes the SQI per segment. Report agreement honestly.
3. **Finalise segmentation** (`03_protocol_segmentation.ipynb`): ACC-based detection of the untagged seated baseline
   in V2 exercise sessions; resolve S03 and S11_b using movement; define comparable windows across protocol
   versions (e.g. first 30 s of each stress task, last 60 s of each aerobic stage, 0–120 s post-sprint).
4. **Decide preprocessing per signal** and document each choice in `docs/methodology.md`. Truncate the S02
   duplicate; mask TEMP faults; exclude signals listed in the issues registry.
5. **Deliverables:** quality tables and figures; an inclusion matrix (participant × condition × signal × segment);
   the updated methodology. Only then move to exercise-physiology EDA (`04`).
