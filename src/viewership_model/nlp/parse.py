from __future__ import annotations

import re
from dataclasses import dataclass

from viewership_model.data.d1_teams import normalize_team_name

NETWORK_PATTERNS = [
    (r"espn\+", "ESPN+"),
    (r"espn2", "ESPN2"),
    (r"espnu", "ESPNU"),
    (r"espn", "ESPN"),
    (r"accn|acc network", "ACC Network"),
    (r"sec network", "SEC Network"),
    (r"big ten network|btn", "Big Ten Network"),
    (r"cbssn", "CBSSN"),
    (r"peacock", "Peacock"),
    (r"fs1", "FS1"),
    (r"fox", "FOX"),
    (r"cbs", "CBS"),
    (r"tnt", "TNT"),
    (r"flocollege", "FloCollege"),
    (r"astros\.com", "Astros.com"),
]

SPORT_PATTERNS = [
    (r"womens?\s+basketball|women's\s+basketball|wbb", "womens_basketball"),
    (r"mens?\s+basketball|men's\s+basketball|mbb", "mens_basketball"),
    (r"womens?\s+softball|women's\s+softball", "softball"),
    (r"softball", "softball"),
    (r"football", "football"),
    (r"baseball", "baseball"),
    (r"volleyball", "volleyball"),
    (r"gymnastics", "gymnastics"),
    (r"soccer", "soccer"),
    (r"basketball", "basketball"),
]

TEAM_ALIASES = {
    "u of a": "Arizona",
    "ua": "Arizona",
    "university of arizona": "Arizona",
    "bama": "Alabama",
    "njit": "NJIT",
    "arkansas": "Arkansas",
    "uconn": "UConn",
    "nc state": "NC State",
    "ole miss": "Ole Miss",
}


@dataclass
class ParsedQuery:
    raw: str
    sport: str | None
    network: str | None
    team_a: str | None
    team_b: str | None
    home_team: str | None = None
    away_team: str | None = None
    ranked: bool = False
    prime_time: bool = False
    rivalry: bool = False


def _normalize_team(name: str) -> str:
    key = name.strip().lower()
    if key in TEAM_ALIASES:
        return TEAM_ALIASES[key]
    titled = " ".join(part.capitalize() for part in re.split(r"\s+", name.strip()))
    return normalize_team_name(titled)


def parse_query(text: str) -> ParsedQuery:
    raw = text.strip()
    lowered = raw.lower()

    sport = None
    for pattern, slug in SPORT_PATTERNS:
        if re.search(pattern, lowered):
            sport = slug
            break

    network = None
    for pattern, canonical in NETWORK_PATTERNS:
        if re.search(pattern, lowered):
            network = canonical
            break

    cleaned = lowered
    for pattern, _ in SPORT_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    for pattern, _ in NETWORK_PATTERNS:
        cleaned = re.sub(pattern, " ", cleaned)
    cleaned = re.sub(r"\b(on|for|the|a|an|women'?s?|men'?s?)\b", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    team_a = None
    team_b = None
    home_team = None
    away_team = None

    at_match = re.search(
        r"([a-z][a-z0-9\s&\.'-]{0,30}?)\s+(?:@|at)\s+([a-z][a-z0-9\s&\.'-]{0,30})",
        cleaned,
    )
    vs_match = re.search(
        r"([a-z][a-z0-9\s&\.'-]{0,30}?)\s+(?:vs\.?|versus|v\.)\s+([a-z][a-z0-9\s&\.'-]{0,30})$",
        cleaned,
    )
    if not vs_match:
        vs_match = re.search(
            r"([a-z][a-z0-9\s&\.'-]{0,30}?)\s+(?:vs\.?|versus|v\.)\s+([a-z][a-z0-9\s&\.'-]{0,30})",
            cleaned,
        )

    if at_match:
        away_team = _normalize_team(at_match.group(1))
        home_team = _normalize_team(at_match.group(2))
        team_a = away_team
        team_b = home_team
    elif vs_match:
        home_team = _normalize_team(vs_match.group(1))
        away_team = _normalize_team(vs_match.group(2))
        team_a = home_team
        team_b = away_team

    return ParsedQuery(
        raw=raw,
        sport=sport,
        network=network,
        team_a=team_a,
        team_b=team_b,
        home_team=home_team,
        away_team=away_team,
        ranked=bool(re.search(r"\branked\b|\btop\s*25\b", lowered)),
        prime_time=bool(re.search(r"prime\s*time|night game|evening", lowered)),
        rivalry=bool(re.search(r"rivalry", lowered)),
    )
