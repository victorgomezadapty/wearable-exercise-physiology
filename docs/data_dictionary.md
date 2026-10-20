# Data Dictionary

**Dataset:** Wearable Device Dataset from Induced Stress and Structured Exercise Sessions. PhysioNet **v1.0.1**,
DOI [10.13026/he0v-tf17](https://doi.org/10.13026/he0v-tf17). Licence: ODC Attribution (ODC-By).
**Device:** Empatica E4, worn on the **non-dominant wrist**.
**Integrity:** all 707 files verified against the v1.0.1 `SHA256SUMS.txt` (see `notebooks/01_data_understanding.ipynb` §1).

Every value below was checked directly against the files. Where this project's findings differ from the
authors' documentation, both are given.

---

## 1. Units of analysis

| Term | Definition | Count |
|---|---|---|
| **Participant** | One person (`S01`–`S18`, `f01`–`f18`). The experimental unit for all inference | 36 |
| **Condition** | `STRESS`, `AEROBIC`, `ANAEROBIC`. Each was done on a different day | 3 |
| **Session** | One recording folder, e.g. `AEROBIC/S04`. A dropped Bluetooth connection splits one participant-condition into two sessions (`_a`, `_b`) | 100 |
| **Segment** | A protocol phase inside a session (e.g. `tmct`, `rpm_85`, `sprint_2`), cut from the tags | 1,064 |
| **Cohort / protocol version** | `V1` = participants `Sxx` (first collection stage), `V2` = `fxx` (second stage, revised protocols). **Cohort is confounded with sex** (V1: 18 M; V2: 17 F + 1 M) | 2 |

Sessions per condition: STRESS 37 (36 participants; f14 split), AEROBIC 31 (30; S11 split; S12 absent),
ANAEROBIC 32 (31; S16 split).

---

## 2. Raw file layout

```
Wearable_Dataset/<CONDITION>/<SESSION>/{ACC,BVP,EDA,HR,IBI,TEMP,tags}.csv
```

### 2.1 Uniformly-sampled signals (ACC, BVP, EDA, HR, TEMP)

| Row | Content |
|---|---|
| 1 | Session start time, UTC, `YYYY-MM-DD HH:MM:SS` (one copy per column). **De-identified**: shifted by a random number of days (> 1 year), consistently within the whole dataset |
| 2 | Sampling rate in Hz (one copy per column) |
| 3… | Samples, no timestamps. Sample *k* is at `start + k / fs` |

### 2.2 Signal reference

| Code | Variable | fs (header) | fs (documented) | Unit | Columns | Source | Observed range* | Notes |
|---|---|---|---|---|---|---|---|---|
| `ACC` | 3-axis acceleration | **32 Hz** | 32 Hz | 1/64 g (±2 g range → raw −128…127) | x, y, z | Raw sensor | −128 … 127 | \|ACC\| ≈ 1 g at rest (gravity). Saturates at ±127 (±2 g). Axis orientation depends on how the band is worn |
| `BVP` | Blood volume pulse (PPG) | **64 Hz** | 64 Hz | **None** (arbitrary, device-processed) | BVP | Raw sensor (green/red PPG, Empatica-filtered) | −2,275 … 1,711 | Zero-centred. Amplitude is not comparable between sessions. Very sensitive to motion and contact |
| `EDA` | Electrodermal activity (skin conductance) | **4 Hz** | 4 Hz | µS | EDA | Raw sensor | 0 … 75.8 | Session medians: stress 0.65 µS, aerobic 3.8 µS, anaerobic 4.2 µS. Values < 0.05 µS suggest poor contact |
| `TEMP` | Skin temperature | **4 Hz** | 4 Hz | °C | TEMP | Raw sensor (IR thermopile) | 23.4 … 37.7 (valid) | **Fault codes 207–235 °C** in 4 sessions. Needs warm-up time. Affected by airflow and sweat |
| `HR` | Heart rate | **1 Hz** | 1 Hz | bpm | HR | **Derived by Empatica** from BVP | 48 … 197 | Average over a 10-s window. **Starts 10 s after the other signals.** Proprietary algorithm; often implausible during cycling |
| `IBI` | Inter-beat interval | event-based | – | s | t_s, ibi_s | **Derived by Empatica** from BVP | 0.31 … 1.64 s (111,346 beats) | See §2.3 |
| `tags` | Event marks | event-based | – | UTC datetime | – | Participant/researcher button press | – | See §2.4 |

\*Range across all sessions after excluding fault codes. Value ranges by condition are in `data/interim/inventory_quality.csv`.

**Sampling rates:** every header in all 100 sessions matches the documented rate. No session deviates.
Sampling rates differ between signals (64/32/4/4/1 Hz), so any multimodal analysis needs explicit
resampling or window-based aggregation.

### 2.3 `IBI.csv`

| Row | Content |
|---|---|
| 1 | Session start (two columns, same as other files) |
| 2… | `t_s` = time of the beat in seconds from session start; `ibi_s` = interval since the previous detected beat (s) |

- Only beats Empatica considers clean are exported, so the series has **gaps**. Coverage (Σ IBI / recording length) has a
  median of **58% for stress and 19% for both exercise conditions**. The longest gap is 23 min.
- Values are **quantised to 1/64 s (15.625 ms)**, the BVP sample grid. This limits RMSSD and pNN50 precision.
- Median IBI: stress 0.77 s (~78 bpm), aerobic 0.56 s, anaerobic 0.50 s.
- `ANAEROBIC/S01/IBI.csv` is empty (0 bytes). `STRESS/S02/IBI.csv` has a 1959 start date, an embedded second
  export header at row 31 and non-monotonic times. `AEROBIC/f04` has a single beat.

### 2.4 `tags.csv`

- One UTC timestamp per row (1-s resolution). Each row is a press of the E4 button and marks a protocol boundary.
- The authors removed accidental presses. **The recording start counts as boundary 0.** It is not a row in the file.
- Expected counts: Stress V1 **13** (authors' diagram says 12; see protocol summary), Stress V2 9,
  Aerobic V1 12, Aerobic V2 8, Anaerobic V1 7, Anaerobic V2 11.
- `STRESS/f14_a/tags.csv` is empty. In `AEROBIC/f07`, rows 5–6 are out of chronological order.
- The tag→segment mapping is in `docs/protocol_summary.md` and `src/data/protocol.py`.

### 2.5 Synchronisation

- ACC, BVP, EDA, TEMP and IBI share the same start timestamp in every session (except IBI in STRESS/S02 and
  AEROBIC/f04).
- **HR starts exactly +10 s later** in all 100 sessions.
- Files end independently: end times among ACC/BVP/EDA/TEMP differ by median 1.4 s, max 7.5 s.
- Signals are on a common clock, so they can be aligned via `start + k/fs`. **Never align by row index.**

---

## 3. Metadata files

### `subject-info.csv`
| Column | Type | Notes |
|---|---|---|
| `Info` | id | Participant id (`S01`…`f18`). Footnote rows follow the data rows |
| `Gender` | m / f | |
| `Age` | years | Missing (`-`) for f14–f18 |
| `Height (cm)`, `Weight (kg)` | numeric | Missing for f14–f18 |
| `Does physical activity regularly?` | Yes / No | V1: 17/18 Yes; V2: 4/13 Yes (among those reported) |
| `Protocol` | V1 / V2 | |
| `Stress Inducement`, `Aerobic Exercise`, `Anaerobic Exercise` | `Yes` / `-` + asterisks | `*` wrong placement, `**` connection loss, `***` not completed, `****` files with constraints |

File encoding is Latin-1. Parsed by `src/data/empatica.read_subject_info()` into `*_done` (bool) and `*_flag`
(number of asterisks).

| Cohort | n | Female | Age mean (range) | BMI mean | Trains regularly |
|---|---|---|---|---|---|
| V1 | 18 | 0 | 20.3 (18–22) | 23.5 | 17 |
| V2 | 18 | 17 | 25.1 (21–31) | 23.9 | 4 of 13 reported |

Note: the paper states an age range of 19–30. The file contains an 18-year-old (S12) and a 31-year-old (f11).

### `Stress_Level_v1.csv`, `Stress_Level_v2.csv`
Self-reported stress per stress-protocol block, one row per participant. V1 columns: Baseline, Stroop, First Rest,
TMCT, Second Rest, Real Opinion, Opposite Opinion, Subtract. V2 has no Stroop and a different order.
The paper describes a 1–10 scale, but **0 occurs** (S08, f08). Values are reported *before and after* each
block, and the file holds one value per block. Which of the two it holds is not documented.

### `data_constraints.txt`
The authors' list of known problems (10 entries). All are reproduced, together with 15 newly found issues, in
`src/data/issues.py` and exported to `data/interim/known_issues.csv`.

---

## 4. Derived tables (`data/interim/`, produced by notebook 01)

| File | Grain | Key columns |
|---|---|---|
| `inventory_sessions.csv` | session | condition, session_id, subject_id, cohort, is_split, has_<file> |
| `inventory_quality.csv` | session × signal | fs_header, fs_matches_doc, n_samples, duration_min, n_nan, min/median/max, longest_flat_s, repeat_at_sample, pct_* quality checks |
| `inventory_ibi.csv` | session | n_ibi, ibi_coverage_pct, n_gaps_gt3s, longest_gap_s, median_ibi_s, pct_succ_change_gt20, ibi_multiple_of_1_64s |
| `inventory_tags.csv` | session | n_tags, expected_n_tags, first_tag_s, last_tag_s, tag_intervals_s |
| `inventory_sync.csv` | session | <signal>_start_offset_s, <signal>_end_offset_s, max_raw_end_spread_s |
| `segments.csv` | segment | segment, phase, start_s, end_s (s from recording start), duration_s, nominal_s, deviation_s, map_source (`nominal`/`manual`) |
| `hr_by_segment_e4.csv` | segment | mean Empatica HR in the segment (**descriptive only; not quality-checked**) |
| `cadence_lockin_aerobic_v1.csv` | aerobic V1 stage | rpm, hr_e4, bvp_dominant, acc_dominant (per min), lock-in flags |
| `known_issues.csv` | issue | source, condition, session_id, signals, issue, action |

### Segment `phase` vocabulary
`baseline` (seated reference) · `warmup` (unloaded pedalling) · `stress` (cognitive/social task) · `rest` (between
stress tasks) · `exercise` (aerobic stage) · `sprint` (all-out effort) · `cooldown` (unloaded pedalling after
effort) · `recovery` (seated still after exercise) · `transition` (self-report, instructions, setup) · `unknown`.
