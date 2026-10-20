"""Plotting helpers for the data-understanding phase.

Colour roles are fixed so a condition keeps its colour in every figure:
AEROBIC = blue, ANAEROBIC = orange, STRESS = aqua (the first three slots of
a CVD-validated categorical palette). Text is never drawn in series colours.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.data.empatica import Session, acc_magnitude_g

FIG_DIR = Path(__file__).resolve().parents[2] / "reports" / "figures"

COND_COLORS = {"AEROBIC": "#2a78d6", "ANAEROBIC": "#eb6834", "STRESS": "#1baf7a"}
TEXT = "#0b0b0b"
TEXT_2 = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"
# Washes for protocol phases (background shading only)
PHASE_COLORS = {
    "stress": "#f6c9b8", "sprint": "#f6c9b8", "exercise": "#cde2fb",
    "warmup": "#eef3fb", "cooldown": "#e3f3ec", "recovery": "#f3f2ee",
    "rest": "#e3f3ec", "baseline": "#f3f2ee",
}


def set_style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": TEXT_2, "axes.titlecolor": TEXT,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.color": TEXT_2, "ytick.color": TEXT_2, "text.color": TEXT,
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold",
        "lines.linewidth": 1.4, "legend.frameon": False, "figure.dpi": 110,
    })


def save(fig, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


# --------------------------------------------------------------------------

def participation_matrix(info: pd.DataFrame, sessions: pd.DataFrame, issues_by_subject: dict):
    """Subjects x conditions: filled = data present, ring = flagged issue, x = no data."""
    subjects = info["subject_id"].tolist()
    conds = ["STRESS", "AEROBIC", "ANAEROBIC"]
    present = {(r.subject_id, r.condition) for r in sessions.itertuples()}
    fig, ax = plt.subplots(figsize=(11, 3.0))
    for j, c in enumerate(conds):
        for i, s in enumerate(subjects):
            if (s, c) in present:
                flagged = (s, c) in issues_by_subject
                ax.scatter(i, j, s=70, color=COND_COLORS[c], zorder=3,
                           edgecolor=TEXT if flagged else SURFACE, linewidth=1.6 if flagged else 1.2)
            else:
                ax.scatter(i, j, s=30, marker="x", color=TEXT_2, zorder=3, linewidth=1)
    ax.set_yticks(range(3), conds)
    ax.set_xticks(range(len(subjects)), subjects, rotation=90, fontsize=8)
    ax.set_ylim(-0.6, 2.6)
    ax.axvline(17.5, color=TEXT_2, lw=0.8)
    ax.text(8.5, 2.85, "Cohort V1 (S01-S18, male)", ha="center", color=TEXT_2, fontsize=9)
    ax.text(26.5, 2.85, "Cohort V2 (f01-f18, 17 female / 1 male)", ha="center", color=TEXT_2, fontsize=9)
    ax.set_title("Who has data for which protocol", pad=22, loc="left")
    ax.grid(False)
    handles = [plt.Line2D([], [], marker="o", ls="", color=TEXT_2, mec=SURFACE, ms=8, label="data present"),
               plt.Line2D([], [], marker="o", ls="", color=TEXT_2, mec=TEXT, mew=1.6, ms=8, label="present, with a flagged issue"),
               plt.Line2D([], [], marker="x", ls="", color=TEXT_2, ms=6, label="no data")]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    return fig


def strip_by_condition(df: pd.DataFrame, value: str, ylabel: str, title: str, hline=None):
    """Per-session values as a strip plot, grouped by condition x cohort."""
    groups = [(c, v) for c in ["STRESS", "AEROBIC", "ANAEROBIC"] for v in ["V1", "V2"]]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    rng = np.random.default_rng(0)
    for k, (c, v) in enumerate(groups):
        d = df[(df.condition == c) & (df.cohort == v)][value].dropna()
        x = k + rng.uniform(-0.15, 0.15, len(d))
        ax.scatter(x, d, s=26, color=COND_COLORS[c], edgecolor=SURFACE, linewidth=1, zorder=3,
                   alpha=0.95 if v == "V1" else 0.65)
        if len(d):
            ax.plot([k - 0.28, k + 0.28], [d.median()] * 2, color=TEXT, lw=1.6, zorder=4)
    ax.set_xticks(range(len(groups)), [f"{c.title()}\n{v}" for c, v in groups])
    if hline is not None:
        ax.axhline(hline, color=TEXT_2, lw=0.8)
    ax.set_ylabel(ylabel)
    ax.set_title(title, loc="left")
    ax.grid(axis="x", visible=False)
    return fig


def segment_durations(seg: pd.DataFrame, condition: str, cohort: str):
    """Observed segment durations (dots) vs the protocol's nominal duration (bar)."""
    d = seg[(seg.condition == condition) & (seg.cohort == cohort) & (seg.map_source == "nominal")]
    d = d[~d.phase.isin(["transition"])]
    order = list(dict.fromkeys(d.segment))
    fig, ax = plt.subplots(figsize=(max(6, 0.55 * len(order) + 2), 3.4))
    rng = np.random.default_rng(1)
    for k, s in enumerate(order):
        x = d[d.segment == s]
        nominal = x.nominal_s.iloc[0]
        if pd.notna(nominal):
            ax.plot([k - 0.32, k + 0.32], [nominal / 60] * 2, color=TEXT, lw=2, zorder=4, solid_capstyle="butt")
        ax.scatter(k + rng.uniform(-0.18, 0.18, len(x)), x.duration_s / 60, s=18,
                   color=COND_COLORS[condition], edgecolor=SURFACE, linewidth=0.8, zorder=3)
    ax.set_xticks(range(len(order)), order, rotation=45, ha="right")
    ax.set_ylabel("duration (min)")
    ax.set_title(f"{condition.title()} {cohort}: observed segment durations (dots) vs nominal (black bar)", loc="left")
    ax.grid(axis="x", visible=False)
    return fig


def session_overview(session: Session, seg: pd.DataFrame | None = None, title: str | None = None):
    """Stacked raw signals for one session on a common time axis (minutes from
    recording start), with protocol segments shaded."""
    sig = session.signals
    t0 = sig["EDA"].start
    panels = [("HR", "HR (bpm)"), ("BVP", "BVP (a.u.)"), ("EDA", "EDA (µS)"),
              ("TEMP", "TEMP (°C)"), ("ACC", "movement (g)\nSD of |ACC|, 1 s")]
    panels = [p for p in panels if p[0] in sig]
    fig, axes = plt.subplots(len(panels), 1, figsize=(12, 1.55 * len(panels) + 0.6), sharex=True)
    color = COND_COLORS[session.condition]
    for ax, (name, label) in zip(axes, panels):
        s = sig[name]
        off = (s.start - t0).total_seconds()
        t = (s.data.index.values + off) / 60
        if name == "ACC":
            # Movement intensity = dynamic component of the magnitude:
            # rolling SD over 1 s (32 samples). A rolling mean would hide the
            # oscillation because gravity dominates |ACC|.
            y = acc_magnitude_g(s.data).rolling(32, center=True, min_periods=8).std().to_numpy()
        else:
            y = s.data.iloc[:, 0].to_numpy()
        if name == "TEMP":
            y = np.where(y > 45, np.nan, y)
        if name == "BVP":
            ax.plot(t, y, color=color, lw=0.3)
            lim = np.nanpercentile(np.abs(y), 99.5)
            ax.set_ylim(-lim, lim)
        else:
            ax.plot(t, y, color=color, lw=1.1)
        ax.set_ylabel(label, rotation=0, ha="right", va="center")
        if seg is not None and len(seg):
            for r in seg.itertuples():
                pc = PHASE_COLORS.get(r.phase)
                if pc:
                    ax.axvspan(r.start_s / 60, r.end_s / 60, color=pc, lw=0, zorder=0)
    if seg is not None and len(seg):
        top = axes[0]
        for r in seg.itertuples():
            if r.phase in ("stress", "sprint", "exercise") or r.segment in ("baseline", "first_rest", "second_rest", "cooldown", "rest"):
                label = r.segment.replace("rpm_", "") + (" rpm" if r.segment.startswith("rpm_") else "")
                top.text((r.start_s + r.end_s) / 120, 1.02, label.replace("_", " "),
                         transform=top.get_xaxis_transform(), rotation=60, fontsize=7,
                         color=TEXT_2, ha="left", va="bottom")
    axes[-1].set_xlabel("minutes from recording start")
    fig.suptitle(title or f"{session.condition} · {session.session_id}", x=0.01, ha="left",
                 fontweight="bold", y=1.0 + 0.04 * (seg is not None))
    fig.align_ylabels(axes)
    return fig


def hr_by_stage(hr: pd.DataFrame, stages: list[str], title: str):
    """Participant-level E4 HR across ordered protocol stages (spaghetti + median)."""
    fig, ax = plt.subplots(figsize=(10, 4))
    p = hr.pivot_table(index="session_id", columns="segment", values="hr")[stages]
    x = np.arange(len(stages))
    for _, row in p.iterrows():
        ax.plot(x, row.values, color=COND_COLORS["AEROBIC"], alpha=0.35, lw=1.1)
    ax.plot(x, p.median().values, color=TEXT, lw=2.2, marker="o", ms=5, label="median across participants")
    ax.set_xticks(x, [s.replace("rpm_", "") if s.startswith("rpm") else s for s in stages])
    ax.set_ylabel("mean E4 HR in stage (bpm)")
    ax.set_title(title, loc="left")
    ax.legend(loc="upper left")
    ax.grid(axis="x", visible=False)
    return fig
