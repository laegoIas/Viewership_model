"""Import all valuation workbooks (Arizona, NJIT, etc.) into model-ready CSV files."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.load import load_config
from viewership_model.data.valuation_import import load_workbook_entries_from_config, save_merged_import


def main() -> None:
    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]
    workbook_entries = load_workbook_entries_from_config(config, ROOT)

    if not workbook_entries:
        raise FileNotFoundError("No valuation workbooks found. Check config paths.valuation_workbooks.")

    games = save_merged_import(
        workbook_entries,
        games_output=ROOT / paths["games"],
        teams_output=ROOT / paths["teams"],
        networks_output=ROOT / paths["networks"],
        sports=config.get("sports"),
        root=ROOT,
    )

    networks = pd.read_csv(ROOT / paths["networks"])
    key_networks = networks["network"].nunique()

    estimates = int(games["is_estimate"].sum()) if "is_estimate" in games.columns else 0
    print(f"Imported {len(games)} games from {len(workbook_entries)} workbook(s)")
    for path, cfg in workbook_entries:
        subset = games[games["source_sheet"].astype(str).str.startswith(path.name)]
        print(f"  {cfg.home_team}: {len(subset)} games from {path.name}")
    print(f"  Sports: {', '.join(sorted(games['sport'].unique()))}")
    print(f"  Reported viewership rows: {len(games) - estimates}")
    print(f"  Estimated rows (yellow cells): {estimates}")
    print(f"  Networks from KEY tab: {key_networks} unique")
    print(f"  Wrote {paths['games']}, {paths['teams']}, {paths['networks']}")


if __name__ == "__main__":
    main()
