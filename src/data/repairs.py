"""Corrections applied on load (raw files are never modified).

Every entry traces back to src/data/issues.py.
"""

from __future__ import annotations

from .empatica import Session, load_session

# Sessions whose export is duplicated: truncate every uniform signal at this
# time (s from start). STRESS/S02: repeat found at ACC sample 49,542 (32 Hz),
# BVP 99,088 (64 Hz), EDA/TEMP 6,192 (4 Hz) -> 1548 s.
TRUNCATE_AT_S = {("STRESS", "S02"): 1548.0}

# Signals invalid for a whole session (sensor covered, stuck, fault codes, ...)
INVALID_SIGNALS = {
    ("STRESS", "S02"): {"IBI"},                       # corrupted IBI file
    ("STRESS", "f07"): {"BVP", "HR", "IBI", "TEMP"},  # protective dock left on
    ("AEROBIC", "f04"): {"BVP", "HR", "IBI"},         # no usable PPG
    ("AEROBIC", "S07"): {"TEMP"},                     # fault codes 100%
    ("ANAEROBIC", "S02"): {"TEMP"},                   # fault codes 92%
    ("ANAEROBIC", "S05"): {"TEMP"},                   # fault codes 62%
    ("ANAEROBIC", "f09"): {"ACC"},                    # z axis stuck at +127
}


def load_clean_session(condition: str, session_id: str) -> tuple[Session, set[str]]:
    """Load a session, apply truncations, and return the set of invalid signals."""
    s = load_session(condition, session_id)
    cut = TRUNCATE_AT_S.get((condition, session_id))
    if cut is not None:
        for name, sig in s.signals.items():
            offset = (sig.start - s.signals["EDA"].start).total_seconds()
            sig.data = sig.data.loc[: cut - offset]
    return s, set(INVALID_SIGNALS.get((condition, session_id), set()))
