from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from viewership_model.data.calibration_tiers import assign_calibration_tier, compute_calibration_weights
from viewership_model.data.d1_teams import normalize_team_name


@dataclass
class ScoringModel:
    """Viewership = sport_scale * (network_reach/100)^network_power * (combined_pop/100)^team_power"""

    sport_scale: dict[str, float] = field(default_factory=dict)
    team_power: dict[str, float] = field(default_factory=dict)
    network_power: dict[str, float] = field(default_factory=dict)
    default_scale: float = 100_000.0
    default_team_power: float = 1.0
    default_network_power: float = 2.25
    default_network_reach: float = 35.0
    default_team_popularity: float = 35.0

    def predict_viewers(
        self,
        sport: str,
        combined_popularity: float,
        network_reach: float,
    ) -> float:
        scale = self.sport_scale.get(sport, self.default_scale)
        team_pwr = self.team_power.get(sport, self.default_team_power)
        net_pwr = self.network_power.get(sport, self.default_network_power)
        team_factor = (combined_popularity / 100.0) ** team_pwr
        network_factor = (network_reach / 100.0) ** net_pwr
        return max(100.0, scale * network_factor * team_factor)


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cutoff = weights.sum() / 2.0
    cumulative = 0.0
    for value, weight in zip(values, weights):
        cumulative += weight
        if cumulative >= cutoff:
            return float(value)
    return float(values[-1])


def calibrate_scoring_model(
    enriched: pd.DataFrame,
    team_power: float = 1.0,
    config: dict | None = None,
) -> ScoringModel:
    """Learn per-sport scale constants from historical games and the team/network tables."""
    df = enriched.copy()
    if config is None:
        config = {}

    if "calibration_tier" not in df.columns:
        df["calibration_tier"] = assign_calibration_tier(df)

    allowed_tiers = config.get("training", {}).get("calibration_tiers")
    if allowed_tiers:
        df = df[df["calibration_tier"].isin(allowed_tiers)].copy()
    if df.empty:
        raise ValueError("No games remain after calibration tier filter.")

    if "avg_viewers" in df.columns:
        viewers = df["avg_viewers"].astype(float)
    else:
        viewers = df["viewership_millions"].astype(float) * 1_000_000

    team_power = config.get("scoring", {}).get("team_power", 1.0)
    network_power = config.get("scoring", {}).get("network_power", 2.25)

    weights = compute_calibration_weights(df, config)
    team_factor = (df["combined_popularity"] / 100.0) ** team_power
    network_factor = (df["network_reach"] / 100.0) ** network_power
    implied_scale = viewers / np.maximum(team_factor * network_factor, 1e-6)
    df = df.copy()
    df["_implied_scale"] = implied_scale

    sport_scale: dict[str, float] = {}
    team_power_by_sport: dict[str, float] = {}
    network_power_by_sport: dict[str, float] = {}

    for sport, group in df.groupby("sport"):
        w = compute_calibration_weights(group, config)
        sport_scale[sport] = _weighted_median(group["_implied_scale"].values, w)
        team_power_by_sport[sport] = team_power
        network_power_by_sport[sport] = network_power

    default_scale = float(_weighted_median(implied_scale.values, weights))
    return ScoringModel(
        sport_scale=sport_scale,
        team_power=team_power_by_sport,
        network_power=network_power_by_sport,
        default_scale=default_scale,
        default_team_power=team_power,
        default_network_power=network_power,
    )


def lookup_team_popularity(
    team: str,
    sport: str,
    teams: pd.DataFrame,
    default: float = 35.0,
) -> tuple[float, bool]:
    team = normalize_team_name(team)
    match = teams[(teams["team"] == team) & (teams["sport"] == sport)]
    if match.empty:
        match = teams[
            (teams["team"].str.lower() == team.lower()) & (teams["sport"] == sport)
        ]
    if match.empty:
        return default, True
    return float(match.iloc[0]["popularity_score"]), False


def lookup_network_reach(
    network: str,
    sport: str,
    networks: pd.DataFrame,
    default: float = 35.0,
) -> tuple[float, bool]:
    match = networks[(networks["network"] == network) & (networks["sport"] == sport)]
    if match.empty:
        return default, True
    return float(match.iloc[0]["reach_score"]), False


def score_game(
    model: ScoringModel,
    sport: str,
    home_team: str,
    away_team: str,
    network: str,
    teams: pd.DataFrame,
    networks: pd.DataFrame,
) -> dict:
    home_pop, home_default = lookup_team_popularity(home_team, sport, teams, model.default_team_popularity)
    away_pop, away_default = lookup_team_popularity(away_team, sport, teams, model.default_team_popularity)
    network_reach, network_default = lookup_network_reach(network, sport, networks, model.default_network_reach)
    combined = (home_pop + away_pop) / 2.0
    viewers = model.predict_viewers(sport, combined, network_reach)

    return {
        "viewers": viewers,
        "viewership_millions": viewers / 1_000_000,
        "home_popularity": home_pop,
        "away_popularity": away_pop,
        "combined_popularity": combined,
        "network_reach": network_reach,
        "sport_scale": model.sport_scale.get(sport, model.default_scale),
        "team_power": model.team_power.get(sport, model.default_team_power),
        "network_power": model.network_power.get(sport, model.default_network_power),
        "used_default_home": home_default,
        "used_default_away": away_default,
        "used_default_network": network_default,
    }
