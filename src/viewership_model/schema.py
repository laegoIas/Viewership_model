from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Sport = Literal[
    "football",
    "basketball",
    "mens_basketball",
    "womens_basketball",
    "softball",
    "baseball",
    "volleyball",
    "soccer",
    "gymnastics",
]
LocationType = Literal["home", "away", "neutral"]


@dataclass(frozen=True)
class GameRecord:
    """One broadcast game with viewership outcome (for training)."""

    game_id: str
    sport: Sport
    season: int
    week: int
    home_team: str
    away_team: str
    network: str
    conference: str
    location_type: LocationType
    location_city: str
    location_state: str
    is_rivalry: bool
    is_ranked_matchup: bool
    is_prime_time: bool
    viewership_millions: float


@dataclass(frozen=True)
class GamePredictionInput:
    """Features available before a game airs."""

    sport: Sport
    season: int
    week: int
    home_team: str
    away_team: str
    network: str
    conference: str
    location_type: LocationType
    location_city: str
    location_state: str
    is_rivalry: bool = False
    is_ranked_matchup: bool = False
    is_prime_time: bool = False
