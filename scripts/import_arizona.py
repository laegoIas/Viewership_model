"""Import Arizona valuation workbook into model-ready CSV files."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.arizona_import import save_import
from viewership_model.data.load import load_config


def main() -> None:
    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]
    workbook = ROOT / paths["arizona_workbook"]

    if not workbook.exists():
        raise FileNotFoundError(f"Arizona workbook not found: {workbook}")

    games = save_import(
        workbook_path=workbook,
        games_output=ROOT / paths["games"],
        teams_output=ROOT / paths["teams"],
        networks_output=ROOT / paths["networks"],
    )

    estimates = int(games["is_estimate"].sum()) if "is_estimate" in games.columns else 0
    print(f"Imported {len(games)} Arizona games from {workbook.name}")
    print(f"  Sports: {', '.join(sorted(games['sport'].unique()))}")
    print(f"  Reported viewership rows: {len(games) - estimates}")
    print(f"  Estimated rows (yellow cells): {estimates}")
    print(f"  Wrote {paths['games']}, {paths['teams']}, {paths['networks']}")


if __name__ == "__main__":
    main()
