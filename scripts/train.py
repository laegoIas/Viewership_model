"""Train the college athletics viewership model."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.arizona_import import save_import
from viewership_model.data.load import load_config
from viewership_model.models.train import train


def main() -> None:
    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]
    games_path = ROOT / paths["games"]
    workbook_path = ROOT / paths["arizona_workbook"]

    if workbook_path.exists():
        print(f"Importing Arizona workbook: {workbook_path.name}")
        save_import(
            workbook_path=workbook_path,
            games_output=games_path,
            teams_output=ROOT / paths["teams"],
            networks_output=ROOT / paths["networks"],
        )
        print(f"Wrote {games_path}")
    elif not games_path.exists():
        raise FileNotFoundError(
            f"No games data found. Add {workbook_path.name} or run with sample data."
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
