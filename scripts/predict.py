"""Predict viewership for a single college game."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.models.predict import predict_game
from viewership_model.schema import GamePredictionInput


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict game viewership (millions)")
    parser.add_argument("--home", required=True, help="Home team name")
    parser.add_argument("--away", required=True, help="Away team name")
    parser.add_argument("--network", required=True, help="Broadcast network")
    parser.add_argument("--conference", default="SEC", help="Home conference")
    parser.add_argument("--sport", default="football", choices=["football", "basketball", "softball"])
    parser.add_argument("--location", default="home", choices=["home", "away", "neutral"])
    parser.add_argument("--city", default="Unknown")
    parser.add_argument("--state", default="ST")
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--rivalry", action="store_true")
    parser.add_argument("--ranked", action="store_true")
    parser.add_argument("--prime-time", action="store_true")
    args = parser.parse_args()

    game = GamePredictionInput(
        sport=args.sport,
        season=args.season,
        week=args.week,
        home_team=args.home,
        away_team=args.away,
        network=args.network,
        conference=args.conference,
        location_type=args.location,
        location_city=args.city,
        location_state=args.state,
        is_rivalry=args.rivalry,
        is_ranked_matchup=args.ranked,
        is_prime_time=args.prime_time,
    )

    prediction = predict_game(game, ROOT / "config.yaml")
    viewers = prediction * 1_000_000
    print(f"Predicted viewership: {prediction:.3f} million ({viewers:,.0f} viewers)")


if __name__ == "__main__":
    main()
