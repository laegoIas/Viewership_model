"""Preview supplemental research games merged into training data."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.calibration_tiers import tag_marquee_games
from viewership_model.data.load import load_config
from viewership_model.data.research_import import load_all_games


def main() -> None:
    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]
    sports = config.get("sports")

    merged, stats = load_all_games(
        ROOT / paths["games"],
        ROOT / paths.get("research_games", "data/research/games.csv"),
        ROOT / paths.get("research_benchmarks", "data/research/viewership_benchmarks.csv"),
        game_types=config.get("training", {}).get("game_types"),
    )

    if sports:
        merged = merged[merged["sport"].isin(sports)]

    typical_n = int((merged["is_marquee"] == 0).sum())
    marquee_n = int((merged["is_marquee"] == 1).sum())

    print("Research data merge preview (regular season only)")
    print(f"  Arizona games:     {stats['primary_rows']}")
    print(f"  Research games:    {stats['supplemental_rows']}")
    print(f"  Added for training:{stats['added_rows']}")
    print(f"  Total merged:      {stats['merged_rows']}")
    print(f"  Schedule tier (is_marquee=0): {typical_n} (used for training)")
    print(f"  Marquee tier (is_marquee=1): {marquee_n} (excluded when exclude_marquee=true)")
    print()
    print("By sport (merged):")
    counts = merged.groupby("sport").size().sort_values(ascending=False)
    for sport, count in counts.items():
        print(f"  {sport}: {count}")

    research_only = merged[merged["source_sheet"].astype(str).str.startswith("research:")]
    if not research_only.empty:
        print()
        print("Sample research rows:")
        sample = research_only[["sport", "home_team", "away_team", "network", "viewership_millions", "source"]].head(8)
        print(sample.to_string(index=False))


if __name__ == "__main__":
    main()
