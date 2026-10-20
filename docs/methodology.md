# Methodology

A running log of analytical principles and every processing decision, with its reason. Updated each phase.

## Principles

1. **Physiology before modelling.** Understand each signal and protocol before building features or models.
2. **The participant is the experimental unit.** Time windows from one person are not independent observations.
   Statistics use participant-level summaries or mixed models. Validation is participant-grouped
   (GroupKFold / leave-one-subject-out).
3. **Movement ≠ physiological state.** ACC describes movement context. HR, BVP/IBI, EDA and TEMP describe
   physiology. Analyses must show what physiology adds *beyond* movement.
4. **Signal-specific processing.** Each signal gets its own quality checks and preprocessing. No pipeline is applied
   blindly to all of them.
5. **Raw data are immutable.** `data/raw/` is never modified. Corrections live in code (`src/`) and in derived files
   (`data/interim/`, `data/processed/`).
6. **Tags define windows.** Segment boundaries come from the tag files. Nominal protocol durations are never assumed.
7. **Report what was excluded and why.** Every exclusion traces back to `src/data/issues.py` or a quality rule.

## Phase 1: Data Understanding (complete)

| Decision | Reason |
|---|---|
| Use PhysioNet v1.0.1; verify all files by SHA-256 | Reproducibility. Signal files were obtained from the authors' Zenodo mirror (identical bytes) because PhysioNet throttled the download |
| Read sampling rates from file headers | They must be verified, not assumed (all matched the documentation) |
| Align signals by `start + k/fs`, HR on its own start | HR starts +10 s later; files end at different times |
| Prepend the recording start as boundary 0 in tag maps | Same convention as the authors' notebook; the first protocol block has no opening tag |
| Stress V1 map uses 13 tags | All 18 files have 13. The 30-s task positions confirm tags 1–12 follow the diagram |
| Sort tags chronologically before mapping | AEROBIC/f07 has two tags out of order |
| Manual maps for 10 sessions with non-standard tag counts | Documented in `src/data/protocol.py::MANUAL_MAPS` and `docs/protocol_summary.md` |
| IBI reader drops non-numeric rows (logged) | STRESS/S02 has a second export header inside IBI.csv |
| No filtering, resampling, artefact removal or exclusion yet | Phase 1 is descriptive. These decisions need the Phase 2 quality assessment |

Quality checks run in Phase 1 (descriptive flags only; thresholds are deliberately loose):
EDA < 0.05 µS (contact) · TEMP < 30 °C and > 45 °C (contact / fault) · HR outside 40–210 bpm ·
ACC |axis| ≥ 127 (saturation) · BVP exact zeros · longest constant run per signal · repeated 30-s block
(duplicated export) · IBI coverage, gaps > 3 s, successive change > 20% · cadence coincidence of HR and BVP
dominant frequency with the prescribed rpm (aerobic V1).

## Phase 2: Signal processing and quality (`02_signal_quality`, `src/signals/`)

| Decision | Reason |
|---|---|
| 30-s windows, 15-s step, cut only *inside* tag-defined segments; segments of 20–30 s give one window | Long enough for HR and EDA summaries, short enough to resolve 30-s tasks and sprints; never mixes protocol phases |
| Repairs on load, never on disk (`src/data/repairs.py`): truncate STRESS/S02 at 1548 s; blank whole-session signals listed in the issue registry | Duplicated export; covered or faulty sensors |
| **EDA:** 5-sample median filter → 1 Hz low-pass (clean) → 0.05 Hz low-pass (tonic). SCR = rise ≥ max(0.05 µS, 2% of tonic) within 10 s, ≥ 1 s apart | NeuroKit's default cleaning needs fs > 6 Hz. A purely absolute threshold counted sweat-level noise at 20–50 µS as SCRs during exercise |
| **TEMP:** values > 45 °C masked; first 5 min of each recording excluded | Fault codes; band warm-up |
| **ACC:** movement = mean of the 1-s rolling SD of \|ACC\|; rhythm = dominant frequency in 0.7–4 Hz | The dynamic component; a rolling mean hides oscillation because gravity dominates |
| **BVP:** not cleaned; used only for spectral quality (SQI) and an independent dominant-frequency HR estimate | No reference to validate a reconstructed waveform |
| **HR valid** if PPG SQI ≥ 0.40, \|E4 HR − PPG dominant frequency\| ≤ 10 bpm, and no cadence lock-in (HR or PPG within ±4 bpm of cadence or step rate during rhythmic movement) | Thresholds = 5th / 95th percentile of clean seated windows (IBI coverage ≥ 70%). Rules use signal properties, never expected outcomes |
| **HRV only in the seated stress protocol**, segment level, ≥ 60 clean consecutive beats and ≥ 50% coverage | During exercise E4 RMSSD stays at 25–35 ms at HR ~130 bpm, which is not physiological (beat jitter plus 15.6-ms quantisation) |
| Physiological plausibility used only as a **sensitivity check**, never to exclude data | Excluding "implausible" data would bias results toward the textbook answer |

## Phase 3: Segmentation and analysis states (`03_protocol_segmentation`)

| Decision | Reason |
|---|---|
| Resting reference = stress-day seated baseline for everyone | V1 exercise starts with pedalling. V2 exercise "baselines" have ~6× seated movement (group spinning room) |
| `AEROBIC_MODERATE` = 70/75/80 rpm + first 3 min of 85 rpm | Stages shared by V1 and V2 with similar exposure |
| `AEROBIC_PEAK` = last 2 min of the final completed stage | Each person's highest protocol stage (absolute power unknown) |
| `POST_SPRINT` = first 2 min of the cooldown after each sprint | HR is unmeasurable during sprints; the response lags the effort |
| `STRESS_RECOVERY` = second half of each rest | Avoids carry-over from the preceding task |
| AEROBIC/S11_b excluded; S03 cooldown kept | Movement shows S11_b is ambiguous and S03's last block is a real cooldown |

## Phase 4–5: Features and statistics (`05`, `06`, `src/models/stats.py`)

- **Participant first:** windows → participant × state means → statistics across participants.
- Paired differences with **bootstrap 95% CIs** (5,000 resamples of participants), Cohen's d_z, Wilcoxon signed-rank,
  **Holm** correction within each family of tests.
- **Mixed models** `feature ~ state + cohort + (1 | participant)` as confirmation. For the small stress contrast, the
  same-day paired analysis is preferred: the single residual variance of the LMM is inflated by the exercise states.
- **ICC(1)** by the one-way ANOVA estimator within each state. The LMM-based ICC converged to the zero boundary for
  small-variance features.
- **Repeated-measures correlation** (Bakdash & Marusich, 2017) for self-report vs physiology.
- Robustness checks: per cohort, and filtered vs unfiltered HR.

## Phase 6: Classification (`07_classification`, `src/models/classify.py`)

| Decision | Reason |
|---|---|
| Classes: STRESS (stress tasks), AEROBIC (aerobic stages), ANAEROBIC (sprint + first 2 min of recovery) | ANAEROBIC as sprint-only would be pure movement detection, with no measurable HR |
| **Leave-one-subject-out** for all reported metrics; a random window split shown only as a leakage demonstration | 30-s windows of one person are not independent; ICC of HR/EDA is 0.8–0.99 |
| Median imputation **fitted inside each training fold** + explicit missing indicators; balanced class weights | No information from the test participant; imbalance (2,401 / 849 / 668 windows) |
| Macro-F1 and balanced accuracy with participant-bootstrap CIs; confusion matrices; per-participant performance | Accuracy alone is misleading with imbalanced classes |
| Baselines first (logistic regression, depth-4 tree), then random forest and gradient boosting | Complexity added only if it helps. It barely did |
| Modality ablation and a **missingness-shortcut test** (HR-missing indicator alone / with movement) | To separate physiological information from movement and from sensor failure |
| Permutation importance on held-out participants (GroupKFold) | Model-agnostic; read at the modality level because correlated features share credit. SHAP not used: with this level of feature redundancy and a dominant movement feature it would add little beyond permutation importance |
