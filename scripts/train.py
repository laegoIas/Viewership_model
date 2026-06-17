"""Train the college athletics viewership model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.load import load_config
from viewership_model.data.valuation_import import load_workbook_entries_from_config, save_merged_import
from viewership_model.data.research_import import load_all_games
from viewership_model.models.train import train


def main() -> None:
    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]
    games_path = ROOT / paths["games"]
    workbook_entries = load_workbook_entries_from_config(config, ROOT)

    if workbook_entries:
        names = ", ".join(path.name for path, _ in workbook_entries)
        print(f"Importing valuation workbooks: {names}")
        save_merged_import(
            workbook_entries,
            games_output=games_path,
            teams_output=ROOT / paths["teams"],
            networks_output=ROOT / paths["networks"],
            sports=config.get("sports"),
            root=ROOT,
        )
        print(f"Wrote {games_path}")
    elif not games_path.exists():
        raise FileNotFoundError(
            "No games data found. Add valuation workbook(s) to data/ or config paths."
        )

    _, merge_stats = load_all_games(
        games_path,
        ROOT / paths.get("research_games", "data/research/games.csv"),
        ROOT / paths.get("research_benchmarks", "data/research/viewership_benchmarks.csv"),
        game_types=config.get("training", {}).get("game_types"),
    )
    if merge_stats["added_rows"]:
        print(
            f"Research data: +{merge_stats['added_rows']} games "
            f"({merge_stats['merged_rows']} total for training)"
        )

    result = train(ROOT / "config.yaml")
    print("Training complete.")
    print("  Model: team popularity × network reach scales")
    print(f"  Train rows: {result.n_train}")
    print(f"  Test rows:  {result.n_test}")
    print(f"  MAE:  {result.mae:.4f} million viewers")
    print(f"  RMSE: {result.rmse:.4f} million viewers")
    print(f"  R²:   {result.r2:.3f}")
    print(f"  Scoring model saved to {result.model_path}")


if __name__ == "__main__":
    main()
