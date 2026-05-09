"""Genera datos sintéticos para `data/gold/company_year_metrics`.

Uso:
    python scripts/generate_synthetic_data.py

Esto crea carpetas `data/gold/company_year_metrics/launch_year=YYYY/part.parquet`.
"""
from pathlib import Path
import random
import pandas as pd


OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "gold" / "company_year_metrics"


def generate(provider_list=None, start_year=2000, end_year=2025, seed=42):
    random.seed(seed)
    if provider_list is None:
        provider_list = [
            "SpaceX",
            "Arianespace",
            "Roscosmos",
            "ULA",
            "ISRO",
            "JAXA",
            "Blue Origin",
            "Rocket Lab",
        ]

    rows = []
    for year in range(start_year, end_year + 1):
        for provider in provider_list:
            total = random.choices(range(0, 15), weights=[1]*5 + [2]*5 + [3]*5, k=1)[0]
            successful = 0 if total == 0 else random.randint(max(0, total - 3), total)
            success_rate = round((successful / total) * 100, 2) if total > 0 else 0.0
            rows.append(
                {
                    "launch_year": int(year),
                    "provider_name": provider,
                    "total_launches": int(total),
                    "successful_launches": int(successful),
                    "success_rate_pct": float(success_rate),
                }
            )

    df = pd.DataFrame(rows)
    return df


def write_partitioned(df: pd.DataFrame, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    for year, sub in df.groupby("launch_year"):
        year_dir = out_dir / f"launch_year={int(year)}"
        year_dir.mkdir(parents=True, exist_ok=True)
        # write a single parquet file per year
        (year_dir / "part.parquet").write_bytes(sub.to_parquet(index=False, engine="pyarrow"))


def main():
    df = generate(start_year=1957, end_year=2025)
    write_partitioned(df, OUT_DIR)
    print(f"Synthetic data written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
