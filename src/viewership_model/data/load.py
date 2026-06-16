from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def load_config(config_path: Path | str = "config.yaml") -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_games(path: Path | str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "home_team",
        "away_team",
        "network",
        "conference",
        "location_type",
        "viewership_millions",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Games file missing columns: {sorted(missing)}")
    return df


def load_teams(path: Path | str, overrides_path: Path | str | None = None) -> pd.DataFrame:
    teams = pd.read_csv(path)
    if overrides_path and Path(overrides_path).exists():
        overrides = pd.read_csv(overrides_path)
        teams = pd.concat([teams, overrides], ignore_index=True)
        teams = teams.drop_duplicates(subset=["team", "sport"], keep="last")
    return teams


def load_networks(path: Path | str, overrides_path: Path | str | None = None) -> pd.DataFrame:
    networks = pd.read_csv(path)
    if overrides_path and Path(overrides_path).exists():
        overrides = pd.read_csv(overrides_path)
        networks = pd.concat([networks, overrides], ignore_index=True)
        networks = networks.drop_duplicates(subset=["network", "sport"], keep="last")
    return networks
