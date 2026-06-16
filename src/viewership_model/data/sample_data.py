from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


RIVALRIES = {
    ("Alabama", "Auburn"),
    ("Ohio State", "Michigan"),
    ("Texas", "Oklahoma"),
    ("Florida", "Georgia"),
    ("USC", "UCLA"),
    ("Army", "Navy"),
    ("Clemson", "South Carolina"),
    ("Florida State", "Miami"),
    ("Kentucky", "Louisville"),
    ("Kansas", "Kansas State"),
    ("Duke", "North Carolina"),
}


SPORT_SCALES = {
    "football": {
        "base": 0.8,
        "pop": 0.04,
        "reach": 0.025,
        "rivalry": 0.15,
        "ranked": 0.12,
        "prime": 0.18,
        "neutral": 0.08,
        "market": 0.02,
        "noise": 0.35,
        "floor": 0.3,
        "max_week": 15,
    },
    "basketball": {
        "base": 0.35,
        "pop": 0.018,
        "reach": 0.012,
        "rivalry": 0.08,
        "ranked": 0.10,
        "prime": 0.12,
        "neutral": 0.05,
        "market": 0.008,
        "noise": 0.15,
        "floor": 0.08,
        "max_week": 20,
    },
    "softball": {
        "base": 0.04,
        "pop": 0.006,
        "reach": 0.003,
        "rivalry": 0.03,
        "ranked": 0.04,
        "prime": 0.05,
        "neutral": 0.02,
        "market": 0.004,
        "noise": 0.03,
        "floor": 0.02,
        "max_week": 18,
    },
}


def _is_rivalry(home: str, away: str) -> bool:
    pair = tuple(sorted([home, away]))
    return pair in RIVALRIES


def _generate_sport_games(
    teams: pd.DataFrame,
    networks: pd.DataFrame,
    sport: str,
    n_games: int,
    rng: np.random.Generator,
    start_index: int = 0,
) -> list[dict]:
    scale = SPORT_SCALES[sport]
    teams_sport = teams[teams["sport"] == sport].drop_duplicates(subset=["team"])
    networks_sport = networks[networks["sport"] == sport]

    team_names = teams_sport["team"].tolist()
    network_names = networks_sport["network"].tolist()
    if not team_names or not network_names:
        return []

    team_lookup = teams_sport.set_index("team")
    network_lookup = networks_sport.set_index("network")
    prefix = sport[:3].upper()
    rows: list[dict] = []

    for i in range(n_games):
        home, away = rng.choice(team_names, size=2, replace=False)
        network = rng.choice(network_names)
        week = int(rng.integers(1, scale["max_week"] + 1))
        season = int(rng.choice([2022, 2023, 2024, 2025]))
        location_type = rng.choice(["home", "neutral"], p=[0.85, 0.15])
        is_rivalry = _is_rivalry(home, away)
        is_ranked = bool(rng.random() < 0.25)
        is_prime = bool(rng.random() < 0.15)

        home_pop = float(team_lookup.loc[home, "popularity_score"])
        away_pop = float(team_lookup.loc[away, "popularity_score"])
        reach = float(network_lookup.loc[network, "reach_score"])
        market = float(team_lookup.loc[home, "market_size_millions"])

        base = scale["base"] + scale["pop"] * (home_pop + away_pop) / 2
        base += scale["reach"] * reach
        base += scale["rivalry"] * is_rivalry
        base += scale["ranked"] * is_ranked
        base += scale["prime"] * is_prime
        base += scale["market"] * np.log1p(market)
        if location_type == "neutral":
            base += scale["neutral"]

        noise = rng.normal(0, scale["noise"])
        viewership = max(scale["floor"], base + noise)

        rows.append(
            {
                "game_id": f"{prefix}-{season}-W{week:02d}-{start_index + i:04d}",
                "sport": sport,
                "season": season,
                "week": week,
                "home_team": home,
                "away_team": away,
                "network": network,
                "conference": team_lookup.loc[home, "conference"],
                "location_type": location_type,
                "location_city": "Sample City",
                "location_state": "ST",
                "is_rivalry": int(is_rivalry),
                "is_ranked_matchup": int(is_ranked),
                "is_prime_time": int(is_prime),
                "viewership_millions": round(viewership, 3),
            }
        )

    return rows


def generate_sample_games(
    teams_path: Path,
    networks_path: Path,
    output_path: Path,
    sport: str = "football",
    n_games: int = 800,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic historical games for pipeline development."""
    rng = np.random.default_rng(seed)
    teams = pd.read_csv(teams_path)
    networks = pd.read_csv(networks_path)

    sports = ["football", "basketball", "softball"] if sport == "all" else [sport]
    per_sport = max(n_games // len(sports), 100)
    rows: list[dict] = []
    index = 0
    for s in sports:
        sport_rows = _generate_sport_games(teams, networks, s, per_sport, rng, index)
        rows.extend(sport_rows)
        index += len(sport_rows)

    games = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    games.to_csv(output_path, index=False)
    return games
