from __future__ import annotations

from pathlib import Path

import joblib

from viewership_model.data.load import load_config, load_networks, load_teams
from viewership_model.models.scoring import ScoringModel, score_game
from viewership_model.schema import GamePredictionInput


def predict_game(
    game: GamePredictionInput,
    config_path: Path | str = "config.yaml",
) -> float:
    """Estimate viewership in millions from team popularity and network reach scales."""
    config = load_config(config_path)
    paths = config["paths"]
    model_path = Path(paths["model_dir"]) / paths.get("scoring_model", "scoring_model.joblib")

    if not model_path.exists():
        raise FileNotFoundError(
            f"No scoring model at {model_path}. Run scripts/train.py first."
        )

    model: ScoringModel = joblib.load(model_path)
    teams = load_teams(paths["teams"], paths.get("team_overrides"))
    networks = load_networks(paths["networks"], paths.get("network_overrides"))

    result = score_game(
        model,
        sport=game.sport,
        home_team=game.home_team,
        away_team=game.away_team,
        network=game.network,
        teams=teams,
        networks=networks,
    )
    return float(result["viewership_millions"])


def predict_game_detail(
    game: GamePredictionInput,
    config_path: Path | str = "config.yaml",
) -> dict:
    config = load_config(config_path)
    paths = config["paths"]
    model_path = Path(paths["model_dir"]) / paths.get("scoring_model", "scoring_model.joblib")
    if not model_path.exists():
        raise FileNotFoundError(
            f"No scoring model at {model_path}. Run scripts/train.py first."
        )

    model: ScoringModel = joblib.load(model_path)
    teams = load_teams(paths["teams"], paths.get("team_overrides"))
    networks = load_networks(paths["networks"], paths.get("network_overrides"))
    return score_game(
        model,
        sport=game.sport,
        home_team=game.home_team,
        away_team=game.away_team,
        network=game.network,
        teams=teams,
        networks=networks,
    )
