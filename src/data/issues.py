"""Registry of known data issues.

``source`` is either ``data_constraints.txt`` (documented by the dataset
authors) or ``phase1`` (found during Phase 1 data understanding in this
project). ``action`` is the *proposed* handling for Phase 2; nothing has
been removed from the raw data.
"""

from __future__ import annotations

import pandas as pd

ISSUES = [
    # ---------------- documented by the authors ----------------
    dict(condition="STRESS", session_id="S02", signals="ALL", source="data_constraints.txt",
         issue="E4 Connect export duplicated: second half of ACC/BVP/EDA/TEMP repeats the first "
               "(verified: repeats start at sample 49,542 / 99,088 / 6,192 / 6,192). IBI.csv also "
               "has a second export header embedded at row 31, a 1959 start time and "
               "non-monotonic times.",
         action="Truncate raw signals at the repeat point; exclude IBI; treat HR as unreliable."),
    dict(condition="STRESS", session_id="f07", signals="BVP,HR,IBI,TEMP", source="data_constraints.txt",
         issue="Protective dock left on: PPG and temperature sensors covered (BVP p99 amplitude "
               "~16 vs ~180 typical; TEMP < 30 C for 100% of the recording; IBI coverage 0.8%).",
         action="Use only EDA and ACC for this session."),
    dict(condition="STRESS", session_id="f14_a/f14_b", signals="ALL", source="data_constraints.txt",
         issue="Bluetooth loss: baseline in f14_a (no tags), rest of protocol in f14_b.",
         action="Treat as one participant; do not concatenate signals across the gap."),
    dict(condition="AEROBIC", session_id="S03", signals="ALL", source="data_constraints.txt",
         issue="Ended early; tags cover 60-85 rpm only (constraint file says 90 rpm reached).",
         action="Use completed stages only; exclude from peak-effort comparisons."),
    dict(condition="AEROBIC", session_id="S07", signals="ALL", source="data_constraints.txt",
         issue="Ended early after 95 rpm.",
         action="Use completed stages only; exclude from peak-effort comparisons."),
    dict(condition="AEROBIC", session_id="S11_a/S11_b", signals="ALL", source="data_constraints.txt",
         issue="Bluetooth loss during 110 rpm; S11_b content is ambiguous (movement looks like "
               "cooldown rather than 110 rpm).",
         action="Use S11_a stages 60-105 rpm; treat S11_b as unlabelled."),
    dict(condition="AEROBIC", session_id="S12", signals="ALL", source="data_constraints.txt",
         issue="Did not perform the aerobic protocol (no folder).", action="-"),
    dict(condition="ANAEROBIC", session_id="S01", signals="IBI", source="data_constraints.txt",
         issue="IBI.csv is empty.", action="No E4 IBI; re-derive beats from BVP if needed."),
    dict(condition="ANAEROBIC", session_id="S06", signals="ALL", source="data_constraints.txt",
         issue="Last (3rd) sprint missing.", action="Use sprints 1-2."),
    dict(condition="ANAEROBIC", session_id="S16_a/S16_b", signals="ALL", source="data_constraints.txt",
         issue="Bluetooth loss: sprints 1-2 in S16_a, sprints 3-4 in S16_b. Four sprints in a "
               "three-sprint (V1) protocol.",
         action="Use sprints 1-3 for V1 comparability; flag sprint 4."),
    # ---------------- discovered in Phase 1 ----------------
    dict(condition="STRESS", session_id="f14_a", signals="tags", source="phase1",
         issue="tags.csv is an empty file (0 bytes).", action="Whole file = baseline."),
    dict(condition="AEROBIC", session_id="f07", signals="tags", source="phase1",
         issue="tags.csv rows 5 and 6 are out of chronological order.",
         action="Sort tags before segmentation (done in src/data/protocol.py)."),
    dict(condition="AEROBIC", session_id="f05,f06,f07", signals="tags", source="phase1",
         issue="Group session in which the 90/95-rpm stage is essentially absent (tags 5 and 6 "
               "pressed 9-15 s apart).",
         action="Do not use rpm_90_95 for these sessions."),
    dict(condition="AEROBIC", session_id="f04,f09,f10", signals="tags", source="phase1",
         issue="Group session with a ~7-min 90/95-rpm stage (nominal 4:30) and short cooldown.",
         action="Use observed durations; model group session as a factor."),
    dict(condition="ANAEROBIC", session_id="f04", signals="tags", source="phase1",
         issue="First tag at t = 1 s: no pre-protocol baseline recorded.",
         action="No baseline for this session."),
    dict(condition="AEROBIC", session_id="S07", signals="TEMP", source="phase1",
         issue="TEMP holds non-physical values (207-229 C) for 100% of the recording "
               "(sensor fault codes).", action="Exclude TEMP."),
    dict(condition="AEROBIC", session_id="S09", signals="TEMP", source="phase1",
         issue="TEMP non-physical (>200 C) for the first 220 s; remainder < 30 C.",
         action="Mask values > 45 C; interpret low TEMP with caution."),
    dict(condition="ANAEROBIC", session_id="S02", signals="TEMP", source="phase1",
         issue="TEMP non-physical (>200 C) for 91.5% of the recording.", action="Exclude TEMP."),
    dict(condition="ANAEROBIC", session_id="S05", signals="TEMP", source="phase1",
         issue="TEMP non-physical (>200 C) for 61.9% of the recording.",
         action="Mask values > 45 C; likely exclude TEMP."),
    dict(condition="ANAEROBIC", session_id="f09", signals="ACC", source="phase1",
         issue="ACC z-axis stuck at +127 (saturation) for 93% of samples; magnitude invalid.",
         action="Exclude ACC magnitude; x/y axes may still carry movement information."),
    dict(condition="AEROBIC", session_id="f04", signals="BVP,HR,IBI", source="phase1",
         issue="BVP exactly zero for 13.7% of samples (runs up to 75 s); only 1 IBI detected, "
               "yet HR.csv still reports values.",
         action="Treat HR as unreliable; exclude from HR/HRV analyses."),
    dict(condition="AEROBIC,ANAEROBIC", session_id="multiple", signals="HR", source="phase1",
         issue="Empatica HR is often physiologically implausible during cycling (flat, falling "
               "with workload, or very high at low workload). In ~1/4 of aerobic V1 stages HR "
               "or the BVP dominant frequency coincides with the pedalling cadence.",
         action="Phase 2: per-segment HR quality index (BVP SQI, cadence coincidence, "
                "monotonicity with workload) before any HR analysis."),
    dict(condition="ALL", session_id="multiple", signals="IBI", source="phase1",
         issue="E4 IBI coverage is low: median 58% of stress recordings, ~19% of exercise "
               "recordings; gaps up to 23 min. IBI values are quantised to 1/64 s (15.6 ms).",
         action="HRV only in segments meeting a coverage threshold; prefer stress/rest segments; "
                "consider re-deriving beats from BVP."),
    dict(condition="ALL", session_id="multiple", signals="TEMP", source="phase1",
         issue="Skin temperature needs several minutes to equilibrate after the band is put on; "
               "13 sessions have >20% of samples below 30 C.",
         action="Discard the first minutes; analyse within-session change rather than absolute "
                "values."),
    dict(condition="ALL", session_id="ALL", signals="HR", source="phase1",
         issue="HR.csv starts 10 s after the other signals (10-s averaging window).",
         action="Align HR on its own start time, never by sample index."),
]


def issues_table() -> pd.DataFrame:
    return pd.DataFrame(ISSUES)
