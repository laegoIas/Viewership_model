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
    parser = argparse.ArgumentParser(
        description="Estimate viewership — prompts for sport, teams, and network when run interactively"
    )
    parser.add_argument("query", nargs="*", help='Optional plain-English query, e.g. "clemson vs coastal carolina baseball"')
    parser.add_argument("--network", help="Broadcast network if not prompted")
    parser.add_argument("--sport", help="Sport if not prompted")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Do not ask follow-up questions for missing details",
    )
    args = parser.parse_args()

    query_text = " ".join(args.query).strip()
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
    sports = config.get("sports")

    if not args.no_prompt:
        if not query_text:
            print("Viewership estimate — answer each prompt in order.")
        parsed = resolve_query(parsed, networks, interactive=True, sports=sports)

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

    sport_label = game_input.sport.replace("_", " ")
    print("\n--- Conclusion ---")
    print(f"  {game_input.home_team} vs {game_input.away_team}")
    print(f"  {sport_label} on {game_input.network}")
    print(f"  Estimated viewership: {_format_viewers(detail['viewership_millions'])}")
    print("\n  How this was calculated:")
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
        "    Formula: sport_scale x (network/100)^network_power x (combined_teams/100)^team_power"
        f" -> sport_scale={detail['sport_scale']:,.0f}, network_power={detail['network_power']:.2f}"
    )
    if detail["used_default_home"] or detail["used_default_away"] or detail["used_default_network"]:
        print("    Note: default scale used where team/network was not in reference tables.")


if __name__ == "__main__":
    main()
