"""Assemble the folder uploaded as the Kaggle dataset
`vctorandrsgmezlpez/wearable-stress-exercise-physiology`.

    python scripts/kaggle/build_kaggle_bundle.py <out_dir>

Layout (what both Kaggle notebooks expect):
    processed/   derived feature tables and results (data/processed, without windows_raw.csv)
    interim/     inventories, segments, issue registry
    code/src/    the analysis package
    raw/         the original PhysioNet recordings and metadata, unchanged

Needs the raw signals (python -m src.data.download). The bundle is ~240 MB: keep
out_dir outside synced folders.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1])
SKIP = {"windows_raw.csv", ".gitkeep"}

if not (ROOT / "data" / "raw" / "Wearable_Dataset").is_dir():
    sys.exit("data/raw/Wearable_Dataset is missing: run python -m src.data.download first")
if OUT.exists():
    shutil.rmtree(OUT)
for sub in ["processed", "interim"]:
    (OUT / sub).mkdir(parents=True)
    for f in sorted((ROOT / "data" / sub).iterdir()):
        if f.is_file() and f.name not in SKIP:
            shutil.copy2(f, OUT / sub / f.name)
ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".gitkeep")
shutil.copytree(ROOT / "src", OUT / "code" / "src", ignore=ignore)
shutil.copytree(ROOT / "data" / "raw", OUT / "raw", ignore=ignore)

files = [f for f in OUT.rglob("*") if f.is_file()]
print(f"wrote {OUT} ({sum(f.stat().st_size for f in files) / 1e6:.1f} MB, {len(files)} files)")
