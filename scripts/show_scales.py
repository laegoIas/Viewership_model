"""Show team popularity scales for a sport."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.load import load_config, load_teams


def main() -> None:
    parser = argparse.ArgumentParser(description="List team popularity scales for a sport")
    parser.add_argument("--sport", required=True, help="e.g. mens_basketball, football")
    parser.add_argument("--team", help="Filter to one team (e.g. Duke)")
    parser.add_argument("--top", type=int, default=15, help="Show top N teams by popularity")
    args = parser.parse_args()

    config = load_config(ROOT / "config.yaml")
    teams = load_teams(
        ROOT / config["paths"]["teams"],
        config["paths"].get("team_overrides"),
    )
    sport = args.sport.replace(" ", "_")
    subset = teams[teams["sport"] == sport].copy()

    if args.team:
        subset = subset[subset["team"].str.lower() == args.team.lower()]

    if subset.empty:
        print(f"No teams found for sport={sport}")
        return

    subset = subset.sort_values("popularity_score", ascending=False)
    if not args.team:
        subset = subset.head(args.top)

    print(f"Team popularity scale ({sport.replace('_', ' ')}):")
    for row in subset.itertuples():
        print(f"  {row.team:25} {row.popularity_score:5.0f}/100  ({row.conference})")


if __name__ == "__main__":
    main()
