#!/usr/bin/env python3
"""
Split monitoring CSVs into one file per canonical river name.

Uses the same column detection and river_name rules as preprocessing
(`modules.data_preprocessing.preprocess_dataset.load_dataset` + `infer_river_name`).

Examples (from project root):
  python scripts/split_csv_by_river.py
  python scripts/split_csv_by_river.py -i datasets/sample_water_quality.csv
  python scripts/split_csv_by_river.py -i "datasets/River Monitoring Dataset.csv" -o datasets/by_river

Output layout:
  <out_dir>/<source_file_stem>/Sungai Klang.csv
  <out_dir>/<source_file_stem>/Sungai Gombak.csv
  ...
Each file includes river_name, station_code, station_name, date, and parameter columns.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.data_preprocessing.preprocess_dataset import load_dataset  # noqa: E402


def safe_filename(label: str) -> str:
    for c in '<>:"/\\|?*\n\r\t':
        label = label.replace(c, "_")
    s = label.strip()
    return s if s else "unknown_river"


def split_one_csv(csv_path: Path, out_root: Path) -> list[Path]:
    csv_path = csv_path.resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(csv_path)

    df = load_dataset(csv_path.parent, csv_path.name)
    if df.empty:
        print(f"Skip (empty after load): {csv_path.name}")
        return []

    if "river_name" not in df.columns:
        raise RuntimeError(f"load_dataset did not set river_name for {csv_path.name}")

    subdir = out_root / safe_filename(csv_path.stem)
    subdir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for river, grp in df.groupby("river_name", dropna=False):
        name = str(river).strip() if pd.notna(river) else "Unknown River"
        out_path = subdir / f"{safe_filename(name)}.csv"
        grp.to_csv(out_path, index=False)
        written.append(out_path)
        print(f"  {name}: {len(grp)} rows -> {out_path.relative_to(PROJECT_ROOT)}")
    return written


def default_inputs(datasets_dir: Path) -> list[Path]:
    names = [
        "sample_water_quality.csv",
        "River Monitoring Dataset.csv",
    ]
    paths: list[Path] = []
    for n in names:
        p = datasets_dir / n
        if p.is_file():
            paths.append(p)
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description="Split CSV monitoring files by canonical river_name.")
    ap.add_argument(
        "-i",
        "--input",
        nargs="*",
        help="CSV file(s). Default: sample_water_quality.csv and River Monitoring Dataset.csv when present.",
    )
    ap.add_argument(
        "-o",
        "--out",
        type=Path,
        default=PROJECT_ROOT / "datasets" / "by_river",
        help="Output root directory (default: datasets/by_river)",
    )
    ap.add_argument(
        "--datasets-dir",
        type=Path,
        default=PROJECT_ROOT / "datasets",
        help="Used with default -i to resolve filenames (default: datasets/)",
    )
    args = ap.parse_args()

    if args.input:
        inputs = [Path(p).resolve() for p in args.input]
    else:
        inputs = default_inputs(Path(args.datasets_dir))

    if not inputs:
        print("No input files found. Pass -i path/to/file.csv or add CSVs under datasets/.")
        sys.exit(1)

    out_root = Path(args.out).resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    for p in inputs:
        print(f"\n{p.name}:")
        split_one_csv(p, out_root)

    print(f"\nDone. Rivers are under: {out_root}")


if __name__ == "__main__":
    main()
