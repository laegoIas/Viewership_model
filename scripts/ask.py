"""Ask for a viewership estimate in plain English."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.load import load_config, load_networks
from viewership_model.models.predict import predict_game_detail
from viewership_model.nlp.parse import ParsedQuery, parse_query
from viewership_model.nlp.prompt import normalize_network_input, resolve_query
from viewership_model.schema import GamePredictionInput


def _format_viewers(millions: float) -> str:
    viewers = millions * 1_000_000
    if viewers >= 1_000_000:
        return f"{millions:.3f} million ({viewers:,.0f} viewers)"
    return f"{viewers:,.0f} viewers ({millions:.4f} million)"


def _build_prediction_input(parsed) -> GamePredictionInput | None:
    if not parsed.team_a or not parsed.team_b or not parsed.sport or not parsed.network:
        return None

    home_team = parsed.home_team or parsed.team_a
    away_team = parsed.away_team or parsed.team_b

    return GamePredictionInput(
        sport=parsed.sport,
        season=2025,
        week=1,
        home_team=home_team,
        away_team=away_team,
        network=parsed.network,
        conference="Unknown",
        location_type="neutral",
        location_city="Unknown",
        location_state="ST",
        is_rivalry=parsed.rivalry,
        is_ranked_matchup=parsed.ranked,
        is_prime_time=parsed.prime_time,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate viewership from plain English")
    parser.add_argument("query", nargs="*", help='e.g. "clemson vs coastal carolina baseball"')
    parser.add_argument("--network", help="Broadcast network if not in the query")
    parser.add_argument("--sport", help="Sport if not in the query")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Do not ask follow-up questions for missing details",
    )
    args = parser.parse_args()

    query_text = " ".join(args.query).strip()
    if not query_text and not args.no_prompt:
        query_text = input("Describe the game: ").strip()

    parsed = parse_query(query_text) if query_text else parse_query("")
    if args.sport:
        parsed = ParsedQuery(
            raw=parsed.raw,
            sport=args.sport.replace(" ", "_"),
            network=parsed.network,
            team_a=parsed.team_a,
            team_b=parsed.team_b,
            home_team=parsed.home_team,
            away_team=parsed.away_team,
            ranked=parsed.ranked,
            prime_time=parsed.prime_time,
            rivalry=parsed.rivalry,
        )
    if args.network:
        network = normalize_network_input(args.network) or args.network
        parsed = ParsedQuery(
            raw=parsed.raw,
            sport=parsed.sport,
            network=network,
            team_a=parsed.team_a,
            team_b=parsed.team_b,
            home_team=parsed.home_team,
            away_team=parsed.away_team,
            ranked=parsed.ranked,
            prime_time=parsed.prime_time,
            rivalry=parsed.rivalry,
        )

    config = load_config(ROOT / "config.yaml")
    networks = load_networks(ROOT / config["paths"]["networks"])

    if not args.no_prompt:
        parsed = resolve_query(parsed, networks, interactive=True)

    print(f'\nEstimate for: "{query_text or "your game"}"')
    print(
        "  ",
        f"sport={parsed.sport or '?'}",
        f"| network={parsed.network or '?'}",
        f"| {parsed.home_team or parsed.team_a or '?'} vs {parsed.away_team or parsed.team_b or '?'}",
    )

    if not parsed.network and args.no_prompt:
        print("\nNetwork is required. Re-run and add --network ESPN (or drop --no-prompt).")
        return

    game_input = _build_prediction_input(parsed)
    if not game_input:
        print("\nNeed sport, both teams, and network to produce an estimate.")
        return

    try:
        detail = predict_game_detail(game_input, ROOT / "config.yaml")
    except FileNotFoundError as exc:
        print(f"\n{exc}")
        print("Run: py scripts/import_arizona.py && py scripts/train.py")
        return

    print("\nEstimated viewership:")
    print(f"  {game_input.home_team} vs {game_input.away_team}")
    print(f"  {game_input.sport} on {game_input.network}")
    print(f"  {_format_viewers(detail['viewership_millions'])}")
    print("\n  How this was calculated:")
    sport_label = game_input.sport.replace("_", " ")
    print(f"    Sport: {sport_label}")
    print(
        f"    {game_input.home_team} popularity ({sport_label}): "
        f"{detail['home_popularity']:.0f}/100"
    )
    print(
        f"    {game_input.away_team} popularity ({sport_label}): "
        f"{detail['away_popularity']:.0f}/100"
    )
    print(f"    Combined team score: {detail['combined_popularity']:.0f}/100")
    print(
        f"    {game_input.network} reach ({sport_label}): "
        f"{detail['network_reach']:.0f}/100"
    )
    print(
        "    Formula: sport_scale x (network/100) x (combined_teams/100)"
        f" -> sport_scale={detail['sport_scale']:,.0f}"
    )
    if detail["used_default_home"] or detail["used_default_away"] or detail["used_default_network"]:
        print("    Note: default scale used where team/network was not in reference tables.")


if __name__ == "__main__":
    main()
