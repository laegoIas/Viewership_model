from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from viewership_model.data.arizona_import import ARIZONA
from viewership_model.nlp.parse import ParsedQuery


@dataclass
class HistoricalMatch:
    avg_viewers: float
    viewership_millions: float
    is_estimate: bool
    sport: str
    network: str
    home_team: str
    away_team: str
    opponent: str
    game_date: object
    location_type: str
    conference: str
    is_ranked_matchup: int
    is_prime_time: int


def _query_opponent(parsed: ParsedQuery) -> str | None:
    if not parsed.team_a or not parsed.team_b:
        return None
    teams = {parsed.team_a, parsed.team_b}
    if ARIZONA in teams:
        return parsed.team_b if parsed.team_a == ARIZONA else parsed.team_a
    return parsed.team_b


def lookup_historical(games: pd.DataFrame, parsed: ParsedQuery) -> HistoricalMatch | None:
    if games.empty or "opponent" not in games.columns:
        return None

    df = games.copy()
    opponent = _query_opponent(parsed)
    if opponent:
        df = df[df["opponent"].str.lower() == opponent.lower()]

    if parsed.sport:
        df = df[df["sport"] == parsed.sport]

    if parsed.network:
        df = df[df["network"].str.lower() == parsed.network.lower()]

    if df.empty:
        return None

    row = df.sort_values("game_date", ascending=False).iloc[0]
    return HistoricalMatch(
        avg_viewers=float(row["avg_viewers"]),
        viewership_millions=float(row["viewership_millions"]),
        is_estimate=bool(row.get("is_estimate", 0)),
        sport=str(row["sport"]),
        network=str(row["network"]),
        home_team=str(row["home_team"]),
        away_team=str(row["away_team"]),
        opponent=str(row["opponent"]),
        game_date=row.get("game_date"),
        location_type=str(row["location_type"]),
        conference=str(row["conference"]),
        is_ranked_matchup=int(row.get("is_ranked_matchup", 0)),
        is_prime_time=int(row.get("is_prime_time", 0)),
    )
