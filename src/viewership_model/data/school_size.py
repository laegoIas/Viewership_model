"""School enrollment data and size-based popularity helpers."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

# Total student enrollment (approximate, 2023–24). Extend via data/school_enrollment.csv.
KNOWN_ENROLLMENT: dict[str, int] = {
    "Arizona": 53_000,
    "Arizona State": 80_000,
    "Alabama": 39_000,
    "Arkansas": 28_000,
    "Auburn": 32_000,
    "BYU": 35_000,
    "Baylor": 20_000,
    "Boston College": 15_000,
    "Clemson": 22_000,
    "Colorado": 37_000,
    "Duke": 17_000,
    "Florida": 56_000,
    "Florida State": 44_000,
    "Georgia": 41_000,
    "Georgia Tech": 40_000,
    "Illinois": 52_000,
    "Indiana": 48_000,
    "Iowa": 32_000,
    "Iowa State": 31_000,
    "Kansas": 28_000,
    "Kansas State": 22_000,
    "Kentucky": 32_000,
    "Louisville": 23_000,
    "LSU": 37_000,
    "Maryland": 41_000,
    "Miami": 19_000,
    "Michigan": 52_000,
    "Michigan State": 51_000,
    "Minnesota": 54_000,
    "Mississippi State": 23_000,
    "Missouri": 31_000,
    "Nebraska": 25_000,
    "North Carolina": 32_000,
    "NC State": 37_000,
    "Northwestern": 23_000,
    "Notre Dame": 13_000,
    "Ohio State": 61_000,
    "Oklahoma": 29_000,
    "Oklahoma State": 26_000,
    "Ole Miss": 23_000,
    "Oregon": 24_000,
    "Oregon State": 34_000,
    "Penn State": 47_000,
    "Pittsburgh": 29_000,
    "Purdue": 51_000,
    "Rutgers": 50_000,
    "South Carolina": 35_000,
    "Southern California": 48_000,
    "USC": 48_000,
    "Stanford": 17_000,
    "Syracuse": 23_000,
    "Tennessee": 36_000,
    "Texas": 53_000,
    "Texas A&M": 74_000,
    "Texas Tech": 40_000,
    "UCLA": 47_000,
    "UCF": 72_000,
    "UConn": 32_000,
    "Utah": 35_000,
    "Vanderbilt": 14_000,
    "Virginia": 26_000,
    "Virginia Tech": 37_000,
    "Washington": 48_000,
    "West Virginia": 26_000,
    "Wisconsin": 49_000,
    "NJIT": 12_000,
    "Monmouth": 6_400,
    "Villanova": 11_000,
    "Georgetown": 20_000,
    "Marquette": 12_000,
    "Creighton": 9_000,
    "Xavier": 7_000,
    "Butler": 6_000,
    "Providence": 5_000,
    "Seton Hall": 10_000,
    "St. John's": 20_000,
    "DePaul": 22_000,
    "Gonzaga": 8_000,
    "Memphis": 22_000,
    "SMU": 12_000,
    "TCU": 12_000,
    "Houston": 47_000,
    "Cincinnati": 40_000,
    "UCF": 72_000,
    "Boise State": 27_000,
    "San Diego State": 36_000,
    "UNLV": 31_000,
    "New Mexico": 22_000,
    "Wyoming": 12_000,
    "Colorado State": 34_000,
    "Fresno State": 25_000,
    "Coastal Carolina": 10_500,
    "App State": 21_000,
    "James Madison": 22_000,
    "Liberty": 15_000,
    "Marshall": 13_000,
    "Louisiana": 19_000,
    "Southern Miss": 14_000,
    "Troy": 17_000,
    "South Alabama": 15_000,
    "Georgia Southern": 27_000,
    "Louisiana Tech": 12_000,
    "UTSA": 34_000,
    "North Texas": 40_000,
    "Rice": 8_000,
    "Tulane": 14_000,
    "Tulsa": 10_000,
    "Wichita State": 17_000,
    "Dayton": 11_000,
    "Saint Louis": 13_000,
    "VCU": 29_000,
    "Davidson": 6_000,
    "Richmond": 4_000,
    "Saint Mary's": 4_000,
    "San Francisco": 11_000,
    "Loyola Chicago": 17_000,
    "Bradley": 6_000,
    "Drake": 5_000,
    "Murray State": 10_000,
    "Belmont": 8_000,
    "UAB": 22_000,
    "Temple": 35_000,
    "Charlotte": 30_000,
    "FAU": 30_000,
    "FIU": 58_000,
    "Middle Tennessee": 22_000,
    "Western Kentucky": 18_000,
    "Old Dominion": 24_000,
    "Buffalo": 32_000,
    "Akron": 20_000,
    "Kent State": 28_000,
    "Ohio": 28_000,
    "Toledo": 19_000,
    "Ball State": 21_000,
    "Central Michigan": 17_000,
    "Eastern Michigan": 17_000,
    "Western Michigan": 21_000,
    "Northern Illinois": 17_000,
    "Bowling Green": 19_000,
    "UMass": 32_000,
    "Army": 4_500,
    "Navy": 6_000,
    "Air Force": 4_500,
}

CONFERENCE_DEFAULT_ENROLLMENT: dict[str, int] = {
    "SEC": 32_000,
    "Big Ten": 38_000,
    "Big 12": 28_000,
    "ACC": 26_000,
    "Pac-12": 30_000,
    "Big East": 18_000,
    "American": 22_000,
    "Mountain West": 24_000,
    "Atlantic 10": 14_000,
    "Sun Belt": 18_000,
    "MAC": 20_000,
    "CUSA": 18_000,
    "MVC": 12_000,
    "WCC": 10_000,
    "CAA": 12_000,
    "Horizon": 14_000,
    "ASUN": 10_000,
    "Big West": 22_000,
    "Summit League": 10_000,
    "WAC": 14_000,
    "SoCon": 8_000,
    "America East": 10_000,
    "Big Sky": 12_000,
    "Big South": 8_000,
    "Ivy League": 8_000,
    "MAAC": 6_000,
    "NEC": 8_000,
    "OVC": 10_000,
    "Patriot": 6_000,
    "Southland": 12_000,
    "SWAC": 8_000,
    "MEAC": 6_000,
    "FBS Independent": 30_000,
    "FCS Independent": 10_000,
    "Big South-OVC": 8_000,
    "MVFC": 12_000,
    "Pioneer": 4_000,
    "United Athletic": 12_000,
}

DEFAULT_ENROLLMENT = 10_000

# Share of final popularity driven by enrollment (by sport).
ENROLLMENT_BLEND: dict[str, float] = {
    "football": 0.32,
    "mens_basketball": 0.26,
    "womens_basketball": 0.24,
    "baseball": 0.18,
    "softball": 0.18,
}


def load_school_enrollment(root: Path | str) -> dict[str, int]:
    """Return team -> total enrollment, merging CSV with built-in known values."""
    enrollment = dict(KNOWN_ENROLLMENT)

    path = Path(root) / "data" / "school_enrollment.csv"
    if path.exists():
        df = pd.read_csv(path)
        if {"team", "enrollment"}.issubset(df.columns):
            for _, row in df.iterrows():
                team = str(row["team"]).strip()
                try:
                    enrollment[team] = int(row["enrollment"])
                except (TypeError, ValueError):
                    continue
    return enrollment


def enrollment_for_team(
    team: str,
    conference: str,
    enrollment_lookup: dict[str, int],
    normalize=None,
) -> int:
    if normalize:
        team = normalize(team)
    if team in enrollment_lookup:
        return enrollment_lookup[team]
    for key, value in enrollment_lookup.items():
        if key.lower() == team.lower():
            return value
    return CONFERENCE_DEFAULT_ENROLLMENT.get(conference.strip(), DEFAULT_ENROLLMENT)


def market_size_from_enrollment(enrollment: int | float) -> float:
    """Express enrollment as thousands of students (used as market_size_millions)."""
    return round(float(enrollment) / 1000, 2)


def popularity_from_enrollment(enrollment: int | float) -> float:
    """Map total enrollment to a 28–88 popularity component (log scale)."""
    value = max(float(enrollment), 2000)
    log_e = math.log10(value)
    # ~2k students -> ~35, ~10k -> ~52, ~30k -> ~65, ~60k -> ~74
    return round(min(88.0, max(28.0, 28.0 + (log_e - 3.3) * 38.0)), 1)


def blend_popularity(
    core_score: float,
    enrollment: int | float,
    sport: str,
) -> float:
    """Apply enrollment boost/penalty relative to a ~15k-student baseline."""
    weight = ENROLLMENT_BLEND.get(sport, 0.20)
    size_score = popularity_from_enrollment(enrollment)
    delta = (size_score - 50.0) * weight
    return round(min(95.0, max(28.0, core_score + delta)), 1)
