"""Print research-backed scale suggestions from viewership_benchmarks.csv."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BENCHMARKS = ROOT / "data" / "research" / "viewership_benchmarks.csv"


def _suggest_score(value: float, sport_max: float, power: float = 0.35) -> float:
    if sport_max <= 0 or value <= 0:
        return 35.0
    return round(min(100.0, max(15.0, 100.0 * (value / sport_max) ** power)), 1)


def main() -> None:
    df = pd.read_csv(BENCHMARKS)
    df["avg_viewers"] = pd.to_numeric(df["avg_viewers"], errors="coerce")
    networks = df[
        (df["entity_type"] == "network")
        & df["avg_viewers"].notna()
        & (df["metric"] == "network_avg_per_game")
    ].copy()

    print("Suggested network reach (from published averages)\n")
    for sport in sorted(networks["sport"].unique()):
        sport_df = networks[networks["sport"] == sport]
        sport_max = float(sport_df["avg_viewers"].max())
        print(f"=== {sport.replace('_', ' ')} (top network avg: {sport_max:,.0f}) ===")
        for row in sport_df.sort_values("avg_viewers", ascending=False).itertuples():
            reach = _suggest_score(float(row.avg_viewers), sport_max)
            network = row.network if pd.notna(row.network) and str(row.network).strip() else row.entity
            print(f"  {str(network):20} {float(row.avg_viewers):>12,.0f} viewers  ->  reach {reach:5.0f}/100")
        print()

    teams = df[
        (df["entity_type"] == "team")
        & df["avg_viewers"].notna()
        & (df["metric"] == "team_avg_per_game")
    ].copy()
    if not teams.empty:
        print("Suggested team popularity (from published season averages)\n")
        for sport in sorted(teams["sport"].unique()):
            sport_df = teams[teams["sport"] == sport]
            sport_max = float(sport_df["avg_viewers"].max())
            print(f"=== {sport.replace('_', ' ')} (top team avg: {sport_max:,.0f}) ===")
            for row in sport_df.sort_values("avg_viewers", ascending=False).itertuples():
                pop = _suggest_score(float(row.avg_viewers), sport_max)
                print(f"  {row.entity:20} {row.avg_viewers:>12,.0f} viewers  ->  pop {pop:5.0f}/100")
            print()

    print("Full benchmarks: data/research/viewership_benchmarks.csv")
    print("Docs: data/research/README.md")


if __name__ == "__main__":
    main()
