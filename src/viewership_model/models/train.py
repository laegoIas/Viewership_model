from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from viewership_model.data.calibration_tiers import assign_calibration_tier
from viewership_model.data.load import load_config, load_networks, load_teams
from viewership_model.data.research_import import load_all_games
from viewership_model.features.build import enrich_games
from viewership_model.models.scoring import ScoringModel, calibrate_scoring_model, score_game


@dataclass
class TrainResult:
    mae: float
    rmse: float
    r2: float
    n_train: int
    n_test: int
    model_path: Path


def _evaluate(model: ScoringModel, df: pd.DataFrame, teams: pd.DataFrame, networks: pd.DataFrame) -> np.ndarray:
    preds = []
    for row in df.itertuples():
        result = score_game(
            model,
            sport=str(row.sport),
            home_team=str(row.home_team),
            away_team=str(row.away_team),
            network=str(row.network),
            teams=teams,
            networks=networks,
        )
        preds.append(result["viewership_millions"])
    return np.array(preds)


def _filter_games_by_sport(games: pd.DataFrame, config: dict) -> pd.DataFrame:
    sports = config.get("sports")
    if sports and "sport" in games.columns:
        return games[games["sport"].isin(sports)].copy()
    sport_filter = config.get("sport", "all")
    if sport_filter != "all" and "sport" in games.columns:
        return games[games["sport"] == sport_filter].copy()
    return games


def train(config_path: Path | str = "config.yaml") -> TrainResult:
    config = load_config(config_path)
    paths = config["paths"]

    games, _merge_stats = load_all_games(
        paths["games"],
        paths.get("research_games"),
        paths.get("research_benchmarks"),
        game_types=config.get("training", {}).get("game_types"),
    )
    if games.empty:
        raise FileNotFoundError(f"No games data found at {paths['games']}")
    games = _filter_games_by_sport(games, config)
    if games.empty:
        raise ValueError("No games remain after sport filter. Check config sports list.")
    teams = load_teams(paths["teams"], paths.get("team_overrides"))
    networks = load_networks(paths["networks"], paths.get("network_overrides"))
    star_weight = config.get("scoring", {}).get("star_weight", 0.65)

    enriched = enrich_games(games, teams, networks, star_weight=star_weight)
    enriched["calibration_tier"] = assign_calibration_tier(enriched)
    if "viewership_millions" not in enriched.columns:
        raise ValueError("Training requires viewership_millions in games data.")

    train_df, test_df = train_test_split(
        enriched,
        test_size=config["model"]["test_size"],
        random_state=config["model"]["random_state"],
    )

    team_power = config.get("scoring", {}).get("team_power", 1.0)
    model = calibrate_scoring_model(train_df, team_power=team_power, config=config)
    preds = _evaluate(model, test_df, teams, networks)
    y_test = test_df["viewership_millions"].values

    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    r2 = float(r2_score(y_test, preds))

    model_dir = Path(paths["model_dir"])
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / paths.get("scoring_model", "scoring_model.joblib")
    joblib.dump(model, model_path)

    metadata = {
        "sports": config.get("sports") or config.get("sport", "all"),
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
        "formula": "viewers = sport_scale * (network_reach/100)^network_power * (combined_pop/100)^team_power",
    }
    joblib.dump(metadata, model_dir / paths["model_file"])

    return TrainResult(
        mae=mae,
        rmse=rmse,
        r2=r2,
        n_train=len(train_df),
        n_test=len(test_df),
        model_path=model_path,
    )
