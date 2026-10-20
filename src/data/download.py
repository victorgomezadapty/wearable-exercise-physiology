"""Download PhysioNet 'wearable-device-dataset' v1.0.1 into data/raw and verify
every file against the official SHA256SUMS.txt.

    python -m src.data.download            # download missing files, then verify
    python -m src.data.download --verify   # verify only

PhysioNet can be slow (it throttles per connection), so files are fetched in
parallel and existing files that already match their checksum are skipped.
The authors' 34 MB notebook is skipped unless --with-notebook is given.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .empatica import RAW_ROOT

BASE_URL = "https://physionet.org/files/wearable-device-dataset/1.0.1/"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(root: Path) -> list[tuple[str, str]]:
    sums = root / "SHA256SUMS.txt"
    if not sums.exists():
        urllib.request.urlretrieve(BASE_URL + "SHA256SUMS.txt", sums)
    rows = [line.split(maxsplit=1) for line in sums.read_text().splitlines() if line.strip()]
    return [(h, p.strip()) for h, p in rows]


def fetch(item: tuple[str, str], root: Path) -> tuple[str, bool]:
    digest, rel = item
    dest = root / rel
    if dest.exists() and sha256(dest) == digest:
        return rel, True
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(BASE_URL + rel, dest)
    return rel, sha256(dest) == digest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="only verify existing files")
    ap.add_argument("--with-notebook", action="store_true")
    ap.add_argument("--workers", type=int, default=16)
    args = ap.parse_args(argv)

    root = RAW_ROOT
    root.mkdir(parents=True, exist_ok=True)
    items = [i for i in manifest(root) if args.with_notebook or not i[1].endswith(".ipynb")]

    if args.verify:
        results = [(rel, (root / rel).exists() and sha256(root / rel) == h) for h, rel in items]
    else:
        with ThreadPoolExecutor(args.workers) as ex:
            results = list(ex.map(lambda i: fetch(i, root), items))

    bad = [rel for rel, ok in results if not ok]
    print(f"{len(results) - len(bad)} / {len(results)} files verified")
    for rel in bad:
        print("  MISMATCH/MISSING:", rel)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
