"""Generate per-river CSV files for S01, S02, S06, S07 under datasets/by_river/."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "datasets" / "by_river" / "sample_water_quality"
SAMPLE = ROOT / "datasets" / "sample_water_quality.csv"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sample = pd.read_csv(SAMPLE)
    sample = sample[sample["date"].astype(str).str[:4].astype(int) <= 2025].copy()

    for code, name in [("S01", "Sungai Klang"), ("S02", "Sungai Gombak")]:
        sub = sample[sample["station_code"] == code].copy()
        sub = sub[["date", "station_code", "DO", "BOD", "COD", "AN", "TSS", "pH"]]
        sub = sub.rename(columns={"TSS": "SS"})
        out = OUT_DIR / f"{name}.csv"
        sub.to_csv(out, index=False)
        print(f"Wrote {out.name}: {len(sub)} rows")

    base = sample[sample["station_code"] == "S04"].copy()
    profiles = {
        "S06": {"name": "Sungai Sarawak", "do_off": 0.3, "bod_off": -0.1, "ss_off": -5, "seed": 6},
        "S07": {"name": "Sungai Kinabatangan", "do_off": 0.5, "bod_off": -0.15, "ss_off": -8, "seed": 7},
    }

    for code, profile in profiles.items():
        r = np.random.default_rng(profile["seed"])
        dates = pd.date_range("2023-01-01", "2025-12-31", freq="3D")
        rows = []
        for i, d in enumerate(dates):
            ref = base.iloc[i % len(base)]
            rows.append(
                {
                    "date": d.strftime("%Y-%m-%d"),
                    "station_code": code,
                    "DO": float(np.clip(ref["DO"] + profile["do_off"] + r.normal(0, 0.4), 1.0, 10.0)),
                    "BOD": float(np.clip(ref["BOD"] + profile["bod_off"] + r.normal(0, 0.3), 0.1, 8.0)),
                    "COD": float(np.clip(ref["COD"] + r.normal(0, 1.5), 1.0, 80.0)),
                    "AN": float(np.clip(ref["AN"] + r.normal(0, 0.15), 0.01, 2.5)),
                    "SS": float(np.clip(ref["TSS"] + profile["ss_off"] + r.normal(0, 8), 1.0, 120.0)),
                    "pH": float(np.clip(ref["pH"] + r.normal(0, 0.25), 5.5, 8.8)),
                }
            )
        df = pd.DataFrame(rows)
        out = OUT_DIR / f"{profile['name']}.csv"
        df.to_csv(out, index=False)
        print(f"Wrote {out.name}: {len(df)} rows")

    print("All CSV files:", sorted(p.name for p in OUT_DIR.glob("*.csv")))


if __name__ == "__main__":
    main()
