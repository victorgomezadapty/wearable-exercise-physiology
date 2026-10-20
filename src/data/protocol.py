"""Protocol definitions and tag-based segmentation.

Tag -> segment mappings come from the protocol diagrams embedded in the
authors' notebook (Wearable_Dataset.ipynb, PhysioNet v1.0.1) and the
Scientific Data paper (Hongn et al., 2025). Boundaries are expressed as
indices into the list ``[recording_start, tag1, tag2, ..., tagN, recording_end]``
so that index 0 is the recording start and index -1 the recording end, the
same convention the authors use in their notebook.

Nominal durations are the *planned* durations from the protocol diagrams.
Observed durations differ, sometimes substantially, and must be measured
from the tags, never assumed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .empatica import Session


@dataclass(frozen=True)
class Segment:
    label: str
    start_idx: int   # index into [rec_start, tag1..tagN, rec_end]
    end_idx: int
    phase: str       # baseline | warmup | stress | rest | exercise | sprint | cooldown | recovery | transition
    nominal_s: float | None = None
    detail: str = ""


END = -1  # recording end

PROTOCOLS: dict[tuple[str, str], dict] = {
    ("STRESS", "V1"): dict(
        # The authors' diagram shows 12 tags, but every V1 file has 13: tags
        # 1-12 follow the diagram and tag 13 is an extra closing press
        # 12-44 s after the subtraction task (verified on all 18 sessions).
        n_tags=13,
        segments=[
            Segment("pre_baseline", 0, 1, "transition", None, "setup before first tag"),
            Segment("baseline", 1, 2, "baseline", 180, "seated, quiet room"),
            Segment("sl_report_1", 2, 3, "transition", None, "self-report / instructions"),
            Segment("stroop", 3, 4, "stress", 120, "Stroop colour-word test"),
            Segment("first_rest", 4, 5, "rest", 300),
            Segment("tmct", 5, 6, "stress", 180, "Trier Mental Challenge Test (arithmetic + noise)"),
            Segment("second_rest", 6, 7, "rest", 300),
            Segment("real_opinion", 7, 8, "stress", 30, "speak own opinion on controversial topic"),
            Segment("sl_report_2", 8, 9, "transition", None),
            Segment("opposite_opinion", 9, 10, "stress", 30, "defend the opposite opinion"),
            Segment("sl_report_3", 10, 11, "transition", None),
            Segment("subtract", 11, 12, "stress", 30, "count back from 1022 by 13 aloud"),
            Segment("sl_report_4", 12, 13, "transition", None, "final self-report"),
            Segment("post", 13, END, "transition", None),
        ],
    ),
    ("STRESS", "V2"): dict(
        n_tags=9,
        segments=[
            Segment("baseline", 0, 1, "baseline", None, "remote session; duration not specified"),
            Segment("sl_report_1", 1, 2, "transition", None),
            Segment("tmct", 2, 3, "stress", 180, "Trier Mental Challenge Test"),
            Segment("first_rest", 3, 4, "rest", 600, "relaxing video"),
            Segment("real_opinion", 4, 5, "stress", 30),
            Segment("sl_report_2", 5, 6, "transition", None),
            Segment("opposite_opinion", 6, 7, "stress", 30),
            Segment("second_rest", 7, 8, "rest", 600, "relaxing video"),
            Segment("subtract", 8, 9, "stress", 30),
            Segment("post", 9, END, "transition", None),
        ],
    ),
    ("AEROBIC", "V1"): dict(
        n_tags=12,
        segments=[
            Segment("warmup", 0, 1, "warmup", 180, "unloaded pedalling (no seated baseline)"),
            *[Segment(f"rpm_{r}", i, i + 1, "exercise", d, f"{r} rpm, {res}")
              for i, (r, d, res) in enumerate(
                  [(60, 180, "20% max res."), (70, 180, "~25%"), (75, 180, "30%"),
                   (80, 180, "35%"), (85, 180, "40%"), (90, 120, "45%"), (95, 120, "50%"),
                   (100, 120, "50%"), (105, 120, "50%"), (110, 120, "50%")], start=1)],
            Segment("cooldown", 11, 12, "cooldown", 240, "unloaded pedalling"),
            Segment("rest", 12, END, "recovery", 120, "seated still"),
        ],
    ),
    ("AEROBIC", "V2"): dict(
        n_tags=8,
        segments=[
            Segment("baseline_warmup", 0, 1, "warmup", 405,
                    "4:30 baseline + 2:15 warm-up; not separated by a tag"),
            Segment("rpm_70", 1, 2, "exercise", 90),
            Segment("rpm_75", 2, 3, "exercise", 90),
            Segment("rpm_80", 3, 4, "exercise", 90),
            Segment("rpm_85", 4, 5, "exercise", 675),
            Segment("rpm_90_95", 5, 6, "exercise", 270, "90 or 95 rpm depending on participant"),
            Segment("cooldown", 6, 7, "cooldown", 180),
            Segment("rest", 7, 8, "recovery", 120, "seated on bike, still"),
            Segment("post", 8, END, "transition", None),
        ],
    ),
    ("ANAEROBIC", "V1"): dict(
        n_tags=7,
        segments=[
            Segment("warmup", 0, 1, "warmup", 180, "unloaded pedalling (no seated baseline)"),
            Segment("sprint_1", 1, 2, "sprint", 30, "all-out, high resistance"),
            Segment("cooldown_1", 2, 3, "cooldown", 240),
            Segment("sprint_2", 3, 4, "sprint", 30),
            Segment("cooldown_2", 4, 5, "cooldown", 240),
            Segment("sprint_3", 5, 6, "sprint", 30),
            Segment("cooldown_3", 6, 7, "cooldown", 240),
            Segment("rest", 7, END, "recovery", 120, "seated still"),
        ],
    ),
    ("ANAEROBIC", "V2"): dict(
        n_tags=11,
        segments=[
            Segment("baseline", 0, 1, "baseline", 270),
            Segment("warmup", 1, 2, "warmup", 270),
            Segment("sprint_1", 2, 3, "sprint", 45),
            Segment("cooldown_1", 3, 4, "cooldown", 255),
            Segment("sprint_2", 4, 5, "sprint", 45),
            Segment("cooldown_2", 5, 6, "cooldown", 225),
            Segment("sprint_3", 6, 7, "sprint", 45),
            Segment("cooldown_3", 7, 8, "cooldown", 225),
            Segment("sprint_4", 8, 9, "sprint", 45),
            Segment("cooldown_4", 9, 10, "cooldown", 225),
            Segment("rest", 10, 11, "recovery", 120),
            Segment("post", 11, END, "transition", None),
        ],
    ),
}


# --------------------------------------------------------------------------
# Sessions whose tag count does not match the protocol (documented in
# data_constraints.txt or discovered in Phase 1). Mappings were derived from
# the tag intervals and checked against the constraint notes.
# --------------------------------------------------------------------------
_AER_V1_RPM = [60, 70, 75, 80, 85, 90, 95, 100, 105, 110]


def _rpm_segments(rpms, first_idx=1):
    return [Segment(f"rpm_{r}", first_idx + i, first_idx + i + 1, "exercise",
                    180 if r <= 85 else 120) for i, r in enumerate(rpms)]


MANUAL_MAPS: dict[tuple[str, str], dict] = {
    ("AEROBIC", "S03"): dict(
        n_tags=7,
        note="Stopped early. Tags cover 60-85 rpm then a 240-s block = cooldown. "
             "Constraint file says 90 rpm was reached; any 90-rpm pedalling is untagged "
             "and would sit inside 'cooldown'.",
        segments=[Segment("warmup", 0, 1, "warmup", 180), *_rpm_segments(_AER_V1_RPM[:5]),
                  Segment("cooldown", 6, 7, "cooldown", 240, "may contain partial 90 rpm"),
                  Segment("rest", 7, END, "recovery", 120)],
    ),
    ("AEROBIC", "S07"): dict(
        n_tags=9,
        note="Stopped after 95 rpm (consistent with data_constraints.txt).",
        segments=[Segment("warmup", 0, 1, "warmup", 180), *_rpm_segments(_AER_V1_RPM[:7]),
                  Segment("cooldown", 8, 9, "cooldown", 240),
                  Segment("rest", 9, END, "recovery", 120)],
    ),
    ("AEROBIC", "S11_a"): dict(
        n_tags=10,
        note="Connection lost during 110 rpm; file ends ~60 s into that stage.",
        segments=[Segment("warmup", 0, 1, "warmup", 180), *_rpm_segments(_AER_V1_RPM[:9]),
                  Segment("rpm_110_partial", 10, END, "exercise", None)],
    ),
    ("AEROBIC", "S11_b"): dict(
        n_tags=1,
        note="Starts ~3.7 min after S11_a ends. Constraint file says it holds the last "
             "110-rpm block, but wrist movement before the tag is low (cooldown-like) "
             "and near-still after it. Treated as ambiguous.",
        segments=[Segment("ambiguous_pedalling", 0, 1, "unknown", None),
                  Segment("rest_probable", 1, END, "recovery", 120)],
    ),
    ("ANAEROBIC", "S06"): dict(
        n_tags=5,
        note="Last sprint missing (data_constraints.txt).",
        segments=[Segment("warmup", 0, 1, "warmup", 180),
                  Segment("sprint_1", 1, 2, "sprint", 30), Segment("cooldown_1", 2, 3, "cooldown", 240),
                  Segment("sprint_2", 3, 4, "sprint", 30), Segment("cooldown_2", 4, 5, "cooldown", 240),
                  Segment("rest", 5, END, "recovery", 120)],
    ),
    ("ANAEROBIC", "S16_a"): dict(
        n_tags=4,
        note="Connection loss; first part with sprints 1-2.",
        segments=[Segment("warmup", 0, 1, "warmup", 180),
                  Segment("sprint_1", 1, 2, "sprint", 30), Segment("cooldown_1", 2, 3, "cooldown", 240),
                  Segment("sprint_2", 3, 4, "sprint", 30),
                  Segment("cooldown_2_partial", 4, END, "cooldown", None)],
    ),
    ("ANAEROBIC", "S16_b"): dict(
        n_tags=5,
        note="Second part with sprints 3-4. S16 performed FOUR sprints although the V1 "
             "protocol specifies three (consistent with data_constraints.txt).",
        segments=[Segment("pre_reconnect", 0, 1, "unknown", None),
                  Segment("sprint_3", 1, 2, "sprint", 30), Segment("cooldown_3", 2, 3, "cooldown", 240),
                  Segment("sprint_4", 3, 4, "sprint", 30), Segment("cooldown_4", 4, 5, "cooldown", 240),
                  Segment("rest", 5, END, "recovery", 120)],
    ),
    ("STRESS", "f14_a"): dict(
        n_tags=0,
        note="Baseline only (connection lost); no tags.",
        segments=[Segment("baseline", 0, END, "baseline", None)],
    ),
    ("STRESS", "f14_b"): dict(
        n_tags=9,
        note="Rest of the protocol after reconnection; the segment before tag 1 is the "
             "end of the baseline, which mostly lives in f14_a.",
        segments=[Segment("baseline_cont", 0, 1, "baseline", None),
                  *[seg for seg in PROTOCOLS[("STRESS", "V2")]["segments"][1:]]],
    ),
}


def cohort_of(session_id: str) -> str:
    return "V1" if session_id.startswith("S") else "V2"


def expected_n_tags(condition: str, session_id: str) -> int:
    return PROTOCOLS[(condition, cohort_of(session_id))]["n_tags"]


def boundaries_s(session: Session) -> np.ndarray:
    """[0, tag1, ..., tagN, rec_end] in seconds from the recording start.

    Tags are sorted chronologically: in AEROBIC/f07 two tags are stored out of
    order in the raw file.
    """
    ref = session.signals.get("EDA") or next(iter(session.signals.values()))
    tags = session.tags if session.tags is not None else pd.Series([], dtype="datetime64[ns, UTC]")
    rel = np.sort((tags - ref.start).dt.total_seconds().to_numpy())
    return np.concatenate(([0.0], rel, [ref.duration_s]))


def segment_map_for(session: Session) -> tuple[list[Segment], str]:
    """Return (segments, source) for a session, or ([], reason) if none applies."""
    n_tags = 0 if session.tags is None else len(session.tags)
    manual = MANUAL_MAPS.get((session.condition, session.session_id))
    if manual is not None and manual["n_tags"] == n_tags:
        return manual["segments"], "manual"
    proto = PROTOCOLS[(session.condition, cohort_of(session.session_id))]
    if n_tags == proto["n_tags"]:
        return proto["segments"], "nominal"
    return [], f"unmapped: {n_tags} tags, expected {proto['n_tags']}"


def segment_session(session: Session) -> pd.DataFrame:
    """Label protocol segments from the tags (nominal map or manual override)."""
    segments, source = segment_map_for(session)
    if not segments:
        return pd.DataFrame()
    b = boundaries_s(session)
    rows = []
    for seg in segments:
        s, e = b[seg.start_idx], b[seg.end_idx]
        rows.append(
            dict(condition=session.condition, session_id=session.session_id,
                 subject_id=session.subject_id, cohort=cohort_of(session.session_id),
                 segment=seg.label, phase=seg.phase, start_s=s, end_s=e,
                 duration_s=e - s, nominal_s=seg.nominal_s,
                 deviation_s=(e - s - seg.nominal_s) if seg.nominal_s else np.nan,
                 map_source=source)
        )
    return pd.DataFrame(rows)
