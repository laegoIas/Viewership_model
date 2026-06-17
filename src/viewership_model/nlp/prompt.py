from __future__ import annotations

import re

import pandas as pd

from viewership_model.nlp.parse import NETWORK_PATTERNS, SPORT_PATTERNS, ParsedQuery, _normalize_team


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


def _normalize_sport_input(text: str) -> str:
    cleaned = text.strip().lower()
    if not cleaned:
        return ""
    for pattern, canonical in SPORT_PATTERNS:
        if re.search(pattern, cleaned):
            return canonical
    return cleaned.replace(" ", "_").replace("-", "_")


def prompt_for_sport(sports: list[str] | None = None) -> str:
    print("\nWhat sport is this?")
    if sports:
        labels = ", ".join(s.replace("_", " ") for s in sports)
        print(f"  Options: {labels}")
    else:
        print("  e.g. baseball, softball, football, mens_basketball, womens_basketball")
    while True:
        answer = input("Sport: ").strip()
        sport = _normalize_sport_input(answer)
        if sport:
            return sport
        print("Please enter a sport.")


def prompt_for_team(label: str) -> str:
    print(f"\nEnter {label}:")
    while True:
        answer = input(f"{label}: ").strip()
        if answer:
            return _normalize_team(answer)
        print(f"Please enter {label.lower()}.")


def prompt_for_teams() -> tuple[str, str]:
    """Legacy combined team prompt (plain-English fallback)."""
    team_a = prompt_for_team("Team 1")
    team_b = prompt_for_team("Team 2")
    return team_a, team_b


def resolve_query(
    parsed: ParsedQuery,
    networks: pd.DataFrame,
    interactive: bool = True,
    sports: list[str] | None = None,
) -> ParsedQuery:
    sport = parsed.sport
    network = parsed.network
    team_a = parsed.team_a
    team_b = parsed.team_b

    if interactive:
        if not sport:
            sport = prompt_for_sport(sports)
        if not team_a:
            team_a = prompt_for_team("Team 1")
        if not team_b:
            team_b = prompt_for_team("Team 2")
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
