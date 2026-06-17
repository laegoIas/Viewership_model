"""Build full Division I team popularity table for all configured sports."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.d1_teams import save_d1_teams
from viewership_model.data.load import load_config


def main() -> None:
    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]
    sports = config.get("sports") or [config.get("sport", "all")]
    games_path = ROOT / paths["games"]
    games = None
    if games_path.exists():
        import pandas as pd

        games = pd.read_csv(games_path)

    teams = save_d1_teams(
        ROOT / paths["teams"],
        sports=sports,
        games=games,
        root=ROOT,
    )
    print(f"Wrote {len(teams)} team rows to {paths['teams']}")
    for sport in sports:
        count = int((teams["sport"] == sport).sum())
        print(f"  {sport}: {count} teams")


if __name__ == "__main__":
    main()
