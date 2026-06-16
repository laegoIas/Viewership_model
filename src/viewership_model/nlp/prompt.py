from __future__ import annotations

import re

import pandas as pd

from viewership_model.nlp.parse import NETWORK_PATTERNS, ParsedQuery, _normalize_team


def normalize_network_input(text: str) -> str | None:
    cleaned = text.strip()
    if not cleaned:
        return None
    lowered = cleaned.lower()
    for pattern, canonical in NETWORK_PATTERNS:
        if re.fullmatch(pattern, lowered) or re.search(pattern, lowered):
            return canonical
    return cleaned.title()


def _network_options(sport: str | None, networks: pd.DataFrame) -> list[str]:
    if sport and not networks.empty and "sport" in networks.columns:
        sport_nets = networks[networks["sport"] == sport]["network"].tolist()
        if sport_nets:
            return sorted(set(sport_nets))
    if not networks.empty and "network" in networks.columns:
        return sorted(set(networks["network"].tolist()))
    return ["ESPN", "ESPN+", "ESPN2", "ESPNU", "FOX", "CBSSN", "ACC Network", "FloCollege"]


def prompt_for_network(sport: str | None, networks: pd.DataFrame) -> str:
    options = _network_options(sport, networks)
    print("\nWhat network is the game on?")
    preview = ", ".join(options[:8])
    if len(options) > 8:
        preview += ", ..."
    print(f"  Common options: {preview}")

    while True:
        answer = input("Network: ").strip()
        network = normalize_network_input(answer)
        if network:
            return network
        print("Please enter a network (e.g. ESPN, ESPN+, SEC Network).")


def prompt_for_sport() -> str:
    print("\nWhat sport is this?")
    print("  e.g. baseball, softball, football, mens_basketball, womens_basketball, volleyball")
    while True:
        answer = input("Sport: ").strip().lower()
        if answer:
            return answer.replace(" ", "_")
        print("Please enter a sport.")


def prompt_for_teams() -> tuple[str, str]:
    print("\nWhich teams are playing?")
    while True:
        answer = input('Teams (e.g. "Clemson vs Coastal Carolina"): ').strip()
        match = re.search(
            r"([a-z][a-z0-9\s&\.'-]{0,40}?)\s+(?:vs\.?|versus|@|at)\s+([a-z][a-z0-9\s&\.'-]{0,40})",
            answer.lower(),
        )
        if match:
            return _normalize_team(match.group(1)), _normalize_team(match.group(2))
        print('Use the format "Team A vs Team B".')


def resolve_query(
    parsed: ParsedQuery,
    networks: pd.DataFrame,
    interactive: bool = True,
) -> ParsedQuery:
    sport = parsed.sport
    network = parsed.network
    team_a = parsed.team_a
    team_b = parsed.team_b

    if interactive:
        if not team_a or not team_b:
            team_a, team_b = prompt_for_teams()
        if not sport:
            sport = prompt_for_sport()
        if not network:
            network = prompt_for_network(sport, networks)

    return ParsedQuery(
        raw=parsed.raw,
        sport=sport,
        network=network,
        team_a=team_a,
        team_b=team_b,
        ranked=parsed.ranked,
        prime_time=parsed.prime_time,
        rivalry=parsed.rivalry,
    )
