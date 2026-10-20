"""Readers for Empatica E4 CSV exports as distributed in the PhysioNet
Wearable Device Dataset (v1.0.1, DOI 10.13026/he0v-tf17).

File format (verified against the raw files):

* Uniformly-sampled signals (ACC, BVP, EDA, HR, TEMP)
    row 1 : session start time, UTC, ``YYYY-MM-DD HH:MM:SS`` (one copy per column)
    row 2 : sampling rate in Hz (one copy per column)
    row 3+: samples
* IBI.csv
    row 1 : session start time (two columns)
    row 2+: ``t_from_start_s, ibi_s``
* tags.csv
    one UTC timestamp per row (button presses), no header

Times have been shifted by the dataset authors for de-identification; they
are consistent *within* a session, so relative timing is valid but absolute
dates/times of day are not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = PROJECT_ROOT / "data" / "raw"
DATASET_ROOT = RAW_ROOT / "Wearable_Dataset"

CONDITIONS = ("STRESS", "AEROBIC", "ANAEROBIC")
UNIFORM_SIGNALS = ("ACC", "BVP", "EDA", "HR", "TEMP")
ALL_FILES = ("ACC", "BVP", "EDA", "HR", "IBI", "TEMP", "tags")

# Values documented in Data_Dictionary.csv / the Scientific Data paper.
# They are checked against the file headers, never assumed.
DOCUMENTED_FS = {"ACC": 32.0, "BVP": 64.0, "EDA": 4.0, "HR": 1.0, "TEMP": 4.0}
UNITS = {
    "ACC": "1/64 g (range +/-2 g)",
    "BVP": "arbitrary PPG units (no physical unit)",
    "EDA": "microsiemens (uS)",
    "HR": "beats per minute (10-s moving average, Empatica algorithm)",
    "TEMP": "degrees Celsius",
    "IBI": "seconds",
}
ACC_COLUMNS = ("x", "y", "z")


@dataclass
class Signal:
    name: str
    start: pd.Timestamp
    fs: float
    data: pd.DataFrame  # columns = channels, index = seconds from signal start

    @property
    def n_samples(self) -> int:
        return len(self.data)

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.fs if self.fs else float("nan")

    @property
    def end(self) -> pd.Timestamp:
        return self.start + pd.to_timedelta(self.duration_s, unit="s")

    def to_absolute(self) -> pd.DataFrame:
        """Return the data indexed by absolute (de-identified) UTC time."""
        out = self.data.copy()
        out.index = self.start + pd.to_timedelta(out.index, unit="s")
        out.index.name = "time_utc"
        return out


@dataclass
class Session:
    condition: str
    session_id: str  # folder name, e.g. "S01", "f14_a"
    path: Path
    signals: dict[str, Signal] = field(default_factory=dict)
    ibi: pd.DataFrame | None = None  # columns: t_s, ibi_s (t relative to ibi_start)
    ibi_start: pd.Timestamp | None = None
    tags: pd.Series | None = None  # absolute UTC timestamps

    @property
    def subject_id(self) -> str:
        return subject_from_session(self.session_id)


def subject_from_session(session_id: str) -> str:
    """'f14_a' -> 'f14'; 'S01' -> 'S01'."""
    return session_id.split("_")[0]


def _empty(path: Path) -> bool:
    return (not path.exists()) or path.stat().st_size == 0


def read_signal(path: Path, name: str | None = None) -> Signal | None:
    """Read one uniformly-sampled Empatica signal file."""
    path = Path(path)
    name = name or path.stem
    if _empty(path):
        return None
    header = pd.read_csv(path, header=None, nrows=2)
    start = pd.Timestamp(str(header.iloc[0, 0]), tz="UTC")
    fs = float(header.iloc[1, 0])
    values = pd.read_csv(path, header=None, skiprows=2, dtype=float)
    if name == "ACC":
        values.columns = list(ACC_COLUMNS)
    else:
        values.columns = [name] if values.shape[1] == 1 else [f"{name}_{i}" for i in range(values.shape[1])]
    values.index = np.arange(len(values)) / fs
    values.index.name = "t_s"
    return Signal(name=name, start=start, fs=fs, data=values)


def read_ibi(path: Path) -> tuple[pd.DataFrame | None, pd.Timestamp | None]:
    """Read IBI.csv. Non-numeric rows (e.g. a second export header embedded
    mid-file, seen in STRESS/S02) are dropped; their count is stored in
    ``df.attrs['n_non_numeric_rows']``."""
    path = Path(path)
    if _empty(path):
        return None, None
    with open(path, encoding="utf-8") as fh:
        first = fh.readline().strip()
    if not first:
        return None, None
    start = pd.Timestamp(first.split(",")[0], tz="UTC")
    raw = pd.read_csv(path, header=None, skiprows=1, names=["t_s", "ibi_s"], dtype=str)
    df = raw.apply(pd.to_numeric, errors="coerce")
    bad = df.isna().any(axis=1)
    df = df[~bad].reset_index(drop=True)
    df.attrs["n_non_numeric_rows"] = int(bad.sum())
    return df, start


def read_tags(path: Path) -> pd.Series:
    path = Path(path)
    if _empty(path):
        return pd.Series([], dtype="datetime64[ns, UTC]", name="tag_utc")
    tags = pd.read_csv(path, header=None, names=["tag_utc"])["tag_utc"]
    return pd.to_datetime(tags, utc=True).rename("tag_utc")


def load_session(condition: str, session_id: str, root: Path = DATASET_ROOT) -> Session:
    path = Path(root) / condition / session_id
    s = Session(condition=condition, session_id=session_id, path=path)
    for name in UNIFORM_SIGNALS:
        sig = read_signal(path / f"{name}.csv", name)
        if sig is not None:
            s.signals[name] = sig
    s.ibi, s.ibi_start = read_ibi(path / "IBI.csv")
    s.tags = read_tags(path / "tags.csv")
    return s


def list_sessions(root: Path = DATASET_ROOT) -> pd.DataFrame:
    """One row per session folder found on disk."""
    rows = []
    for cond in CONDITIONS:
        cdir = Path(root) / cond
        if not cdir.exists():
            continue
        for d in sorted(p for p in cdir.iterdir() if p.is_dir()):
            rows.append(
                {
                    "condition": cond,
                    "session_id": d.name,
                    "subject_id": subject_from_session(d.name),
                    "cohort": "V1" if d.name.startswith("S") else "V2",
                    "is_split": "_" in d.name,
                    **{f"has_{f}": not _empty(d / f"{f}.csv") for f in ALL_FILES},
                }
            )
    return pd.DataFrame(rows)


def acc_magnitude_g(acc: pd.DataFrame) -> pd.Series:
    """Euclidean norm of the 3 ACC axes, converted from 1/64 g to g."""
    return np.sqrt((acc[list(ACC_COLUMNS)] ** 2).sum(axis=1)) / 64.0


# --------------------------------------------------------------------------
# Metadata files
# --------------------------------------------------------------------------

def read_subject_info(root: Path = RAW_ROOT) -> pd.DataFrame:
    """Parse subject-info.csv, separating the footnote markers (*, **, ...)
    from the Yes/No/- protocol flags."""
    df = pd.read_csv(Path(root) / "subject-info.csv", encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={"Info": "subject_id"})
    df = df[df["subject_id"].astype(str).str.match(r"^[Sf]\d{2}$", na=False)].copy()
    df = df.replace("-", np.nan)
    for col in ["Age", "Height (cm)", "Weight (kg)"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col, short in [("Stress Inducement", "stress"), ("Aerobic Exercise", "aerobic"),
                       ("Anaerobic Exercise", "anaerobic")]:
        raw = df[col].astype("string")
        df[f"{short}_done"] = raw.str.startswith("Yes").fillna(False).astype(bool)
        df[f"{short}_flag"] = raw.str.count(r"\*").fillna(0).astype(int)
    df["bmi"] = df["Weight (kg)"] / (df["Height (cm)"] / 100) ** 2
    return df.reset_index(drop=True)


FLAG_MEANING = {
    0: "",
    1: "wrong wristband placement",
    2: "connection loss (split file)",
    3: "protocol not fully completed",
    4: "files with constraints/annotations",
}


def read_stress_levels(root: Path = RAW_ROOT) -> dict[str, pd.DataFrame]:
    out = {}
    for v in ("v1", "v2"):
        df = pd.read_csv(Path(root) / f"Stress_Level_{v}.csv", index_col=0)
        df.index.name = "subject_id"
        out[v.upper()] = df
    return out
