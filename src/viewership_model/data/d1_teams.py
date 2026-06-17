from __future__ import annotations

import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

NCAA_STANDINGS_URL = "https://ncaa-api.henrygd.me/standings/{path}"

SPORT_API_PATHS: dict[str, list[str]] = {
    "mens_basketball": ["basketball-men/d1"],
    "womens_basketball": ["basketball-women/d1"],
    "football": ["football/fbs", "football/fcs"],
    "baseball": [],  # filled from basketball roster when API unavailable
    "softball": [],
}

# Conference base popularity by sport (before win-pct adjustment).
CONFERENCE_BASE: dict[str, dict[str, float]] = {
    "mens_basketball": {
        "SEC": 78,
        "Big Ten": 77,
        "Big 12": 76,
        "ACC": 75,
        "Big East": 74,
        "Pac-12": 72,
        "American": 62,
        "Atlantic 10": 61,
        "Mountain West": 60,
        "MVC": 58,
        "WCC": 57,
        "Sun Belt": 56,
        "MAC": 55,
        "CUSA": 54,
        "CAA": 50,
        "Horizon": 49,
        "ASUN": 47,
        "Big West": 46,
        "Summit League": 45,
        "WAC": 44,
        "SoCon": 44,
        "America East": 40,
        "Big Sky": 39,
        "Big South": 39,
        "Ivy League": 42,
        "MAAC": 38,
        "NEC": 36,
        "OVC": 36,
        "Patriot": 41,
        "Southland": 37,
        "SWAC": 34,
        "MEAC": 33,
    },
    "womens_basketball": {
        "SEC": 76,
        "Big Ten": 75,
        "Big 12": 74,
        "ACC": 74,
        "Big East": 78,
        "Pac-12": 70,
        "American": 60,
        "Atlantic 10": 59,
        "Mountain West": 58,
        "MVC": 56,
        "WCC": 55,
        "Sun Belt": 54,
        "MAC": 53,
        "CUSA": 52,
        "CAA": 48,
        "Horizon": 47,
        "ASUN": 45,
        "Big West": 44,
        "Summit League": 43,
        "WAC": 42,
        "SoCon": 42,
        "America East": 38,
        "Big Sky": 37,
        "Big South": 37,
        "Ivy League": 40,
        "MAAC": 36,
        "NEC": 34,
        "OVC": 34,
        "Patriot": 39,
        "Southland": 35,
        "SWAC": 32,
        "MEAC": 31,
    },
    "football": {
        "SEC": 95,
        "Big Ten": 88,
        "Big 12": 86,
        "ACC": 72,
        "Pac-12": 70,
        "American": 55,
        "Mountain West": 52,
        "Sun Belt": 48,
        "MAC": 45,
        "CUSA": 44,
        "FBS Independent": 78,
        "Big Sky": 42,
        "Big South-OVC": 38,
        "CAA": 40,
        "FCS Independent": 36,
        "Ivy League": 34,
        "MEAC": 30,
        "MVFC": 44,
        "NEC": 32,
        "Patriot": 33,
        "Pioneer": 28,
        "SWAC": 30,
        "SoCon": 38,
        "Southland": 36,
        "United Athletic": 37,
    },
    "baseball": {
        "SEC": 82,
        "ACC": 74,
        "Big 12": 72,
        "Pac-12": 70,
        "Big Ten": 68,
        "Sun Belt": 62,
        "American": 58,
        "Atlantic 10": 56,
        "CUSA": 52,
        "Mountain West": 50,
        "Big East": 48,
        "WCC": 46,
        "CAA": 44,
        "MAC": 42,
        "MVC": 42,
        "ASUN": 40,
        "Big West": 40,
        "SoCon": 38,
        "America East": 36,
        "Big South": 36,
        "Horizon": 36,
        "NEC": 32,
        "OVC": 32,
        "Patriot": 34,
        "Southland": 32,
        "SWAC": 30,
        "MEAC": 28,
        "Summit League": 34,
        "WAC": 34,
        "Big Sky": 32,
        "Ivy League": 34,
        "MAAC": 30,
    },
    "softball": {
        "SEC": 88,
        "Big 12": 82,
        "ACC": 72,
        "Pac-12": 70,
        "Big Ten": 68,
        "Sun Belt": 62,
        "American": 58,
        "Mountain West": 52,
        "CUSA": 50,
        "Big East": 48,
        "WCC": 46,
        "Atlantic 10": 44,
        "MVC": 42,
        "MAC": 40,
        "CAA": 38,
        "ASUN": 36,
        "Big West": 36,
        "America East": 34,
        "Big South": 34,
        "Horizon": 34,
        "NEC": 30,
        "OVC": 30,
        "Patriot": 32,
        "Southland": 30,
        "SWAC": 28,
        "MEAC": 26,
        "Summit League": 32,
        "WAC": 32,
        "Big Sky": 30,
        "Ivy League": 32,
        "MAAC": 28,
        "SoCon": 32,
    },
}

DEFAULT_CONFERENCE_BASE = 35.0

TEAM_NAME_FIXES: dict[str, str] = {
    "Florida St.": "Florida State",
    "Miami (FL)": "Miami",
    "Saint Mary's (CA)": "Saint Mary's",
    "St. John's (NY)": "St. John's",
    "LIU": "LIU",
    "UConn": "UConn",
    "USC": "USC",
    "UAB": "UAB",
    "UCF": "UCF",
    "UCLA": "UCLA",
    "UNLV": "UNLV",
    "UTEP": "UTEP",
    "UTSA": "UTSA",
    "SMU": "SMU",
    "TCU": "TCU",
    "LSU": "LSU",
    "BYU": "BYU",
    "N.C. A&T": "North Carolina A&T",
    "N.C. Central": "North Carolina Central",
    "UNC": "North Carolina",
    "NC State": "NC State",
    "Ole Miss": "Ole Miss",
    "Pitt": "Pittsburgh",
    "UMass": "UMass",
    "UAlbany": "UAlbany",
}


def normalize_team_name(name: str) -> str:
    text = str(name).strip()
    if not text:
        return text
    if text in TEAM_NAME_FIXES:
        return TEAM_NAME_FIXES[text]
    text = re.sub(r"^St\. ", "Saint ", text)
    text = re.sub(r"\bSt\.$", " State", text)
    text = re.sub(r"\s*\(FL\)$", "", text)
    return TEAM_NAME_FIXES.get(text, text)


def _fetch_standings(path: str) -> dict:
    url = NCAA_STANDINGS_URL.format(path=path)
    try:
        raw = subprocess.check_output(["/usr/bin/curl", "-s", "--max-time", "20", url])
    except (subprocess.CalledProcessError, FileNotFoundError):
        with urllib.request.urlopen(url, timeout=20) as resp:
            raw = resp.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def _parse_record(row: dict) -> float:
    try:
        wins = float(row.get("Overall W", 0) or 0)
        losses = float(row.get("Overall L", 0) or 0)
    except (TypeError, ValueError):
        return 0.5
    total = wins + losses
    if total <= 0:
        return 0.5
    return wins / total


def fetch_sport_roster(sport: str) -> pd.DataFrame:
    """Return team, conference, win_pct for a sport from NCAA standings."""
    paths = SPORT_API_PATHS.get(sport, [])
    rows: list[dict] = []
    for path in paths:
        payload = _fetch_standings(path)
        for conf_block in payload.get("data", []):
            conference = str(conf_block.get("conference", "Unknown")).strip()
            for team_row in conf_block.get("standings", []):
                school = normalize_team_name(str(team_row.get("School", "")).strip())
                if not school:
                    continue
                rows.append(
                    {
                        "team": school,
                        "conference": conference,
                        "win_pct": _parse_record(team_row),
                        "sport": sport,
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["team", "conference", "win_pct", "sport"])
    df = pd.DataFrame(rows)
    return df.drop_duplicates(subset=["team", "sport"], keep="first").reset_index(drop=True)


def _conference_base(conference: str, sport: str) -> float:
    sport_map = CONFERENCE_BASE.get(sport, {})
    if conference in sport_map:
        return sport_map[conference]
    # Fuzzy match common aliases
    conf_key = conference.strip()
    for key, value in sport_map.items():
        if key.lower() == conf_key.lower():
            return value
    return DEFAULT_CONFERENCE_BASE


def score_team(conference: str, sport: str, win_pct: float = 0.5) -> float:
    base = _conference_base(conference, sport)
    adjustment = (win_pct - 0.5) * 18.0
    return round(min(95.0, max(28.0, base + adjustment)), 1)


def _load_manual_scores(root: Path | str) -> pd.DataFrame:
    root = Path(root)
    rows: list[dict] = []

    overrides = root / "data" / "team_overrides.csv"
    if overrides.exists():
        df = pd.read_csv(overrides)
        for _, row in df.iterrows():
            rows.append(
                {
                    "team": normalize_team_name(str(row["team"])),
                    "sport": str(row["sport"]),
                    "popularity_score": float(row["popularity_score"]),
                    "source": "override",
                }
            )

    benchmarks = root / "data" / "research" / "viewership_benchmarks.csv"
    if benchmarks.exists():
        df = pd.read_csv(benchmarks)
        bench = df[df["entity_type"] == "team"]
        for _, row in bench.iterrows():
            metric = str(row.get("metric", ""))
            if "popularity" not in metric and "team_avg" not in metric:
                continue
            sport = str(row["sport"])
            team = normalize_team_name(str(row["entity"]))
            value = float(row["avg_viewers"])
            if "popularity" in metric:
                score = value
            else:
                # Map avg viewers to popularity for football tiers
                score = min(95.0, max(28.0, 28.0 + (value / 250_000) ** 0.35 * 40))
            rows.append(
                {
                    "team": team,
                    "sport": sport,
                    "popularity_score": round(score, 1),
                    "source": "benchmark",
                }
            )

    if not rows:
        return pd.DataFrame(columns=["team", "sport", "popularity_score", "source"])
    return pd.DataFrame(rows)


WORKBOOK_POPULARITY_CAP_ABOVE_CONFERENCE = 8.0
OUTLIER_VIEWERSHIP_MULTIPLIER = 5.0


def _workbook_owner_from_source(source: str | float | None) -> str | None:
    """Map valuation source_sheet to the school that owns the workbook."""
    if source is None or (isinstance(source, float) and pd.isna(source)):
        return None
    filename = str(source).split(":")[0].strip()
    match = re.match(r"^(.+?)\s+Jersey Patch", filename, re.IGNORECASE)
    if match:
        return normalize_team_name(match.group(1).strip())
    return None


def _workbook_owned_games(sport_games: pd.DataFrame, team: str) -> pd.DataFrame:
    """Games from valuation workbooks owned by this team only."""
    team = normalize_team_name(team)
    source_col = "source_sheet" if "source_sheet" in sport_games.columns else "source"
    if source_col not in sport_games.columns:
        return sport_games.iloc[0:0]
    owned = sport_games[
        sport_games[source_col].apply(lambda s: _workbook_owner_from_source(s) == team)
    ]
    return owned


def _workbook_games_for_team_popularity(sport_games: pd.DataFrame, team: str) -> pd.DataFrame:
    """Home/neutral games from this team's workbook — away visits excluded."""
    team = normalize_team_name(team)
    owned = _workbook_owned_games(sport_games, team)
    if owned.empty:
        return owned
    home = owned[owned["home_team"] == team]
    if "location_type" not in owned.columns:
        return home

    neutral = owned[
        (owned["location_type"] == "neutral")
        & ((owned["home_team"] == team) | (owned["away_team"] == team))
    ]
    if neutral.empty:
        return home
    combined = pd.concat([home, neutral], ignore_index=True)
    if "game_id" in combined.columns:
        return combined.drop_duplicates(subset=["game_id"], keep="first")
    return combined.drop_duplicates(keep="first")


def observed_scores_from_games(
    games: pd.DataFrame,
    team_conferences: dict[tuple[str, str], str] | None = None,
) -> pd.DataFrame:
    """Derive popularity from a team's own workbook home/neutral games only.

    Away games remain in games.csv for training but do not inflate the
    visiting team's popularity (e.g. Monmouth @ Auburn on SEC Network).
    Opponent teams are not scored from another school's workbook.
    """
    if games.empty:
        return pd.DataFrame(columns=["team", "sport", "popularity_score", "source"])

    source_col = "source_sheet" if "source_sheet" in games.columns else "source"
    rows: list[dict] = []
    for sport in sorted(games["sport"].unique()):
        sport_games = games[games["sport"] == sport]
        sport_median = float(sport_games["avg_viewers"].median())
        owners: set[str] = set()
        if source_col in sport_games.columns:
            for src in sport_games[source_col].dropna().unique():
                owner = _workbook_owner_from_source(src)
                if owner:
                    owners.add(owner)
        for team in sorted(owners):
            team_games = _workbook_games_for_team_popularity(sport_games, team)
            if team_games.empty:
                continue

            viewers = team_games["avg_viewers"].astype(float)
            outlier_cap = sport_median * OUTLIER_VIEWERSHIP_MULTIPLIER
            filtered = viewers[viewers <= outlier_cap]
            if not filtered.empty:
                viewers = filtered
            typical_viewers = float(viewers.median())

            popularity = min(
                95.0, max(20.0, 100.0 * (typical_viewers / max(sport_median, 1)) ** 0.35)
            )

            conference = (team_conferences or {}).get((team, sport))
            if not conference:
                conf_series = team_games.loc[team_games["home_team"] == team, "conference"]
                if conf_series.empty and "conference" in team_games.columns:
                    conf_series = team_games["conference"]
                conference = (
                    conf_series.mode().iloc[0] if not conf_series.empty else "Unknown"
                )
            conf_base = _conference_base(str(conference), sport)
            popularity = min(popularity, conf_base + WORKBOOK_POPULARITY_CAP_ABOVE_CONFERENCE)
            popularity = max(popularity, conf_base - 8.0)

            rows.append(
                {
                    "team": team,
                    "conference": conference,
                    "popularity_score": round(popularity, 1),
                    "sport": sport,
                    "source": "workbook",
                }
            )
    return pd.DataFrame(rows)


def build_d1_teams(
    sports: list[str],
    games: pd.DataFrame | None = None,
    root: Path | str | None = None,
) -> pd.DataFrame:
    """Build popularity scores for all D1 teams in each sport."""
    root = Path(root or Path.cwd())
    roster_parts: list[pd.DataFrame] = []

    mbb = fetch_sport_roster("mens_basketball")
    wbb = fetch_sport_roster("womens_basketball")
    if not mbb.empty:
        roster_parts.append(mbb)
    if not wbb.empty:
        roster_parts.append(wbb)

    for sport in sports:
        if sport in {"baseball", "softball"}:
            proxy = mbb.copy()
            proxy["sport"] = sport
            roster_parts.append(proxy)
        elif sport == "football":
            fb = fetch_sport_roster("football")
            if not fb.empty:
                roster_parts.append(fb)
        elif sport not in {"mens_basketball", "womens_basketball"}:
            proxy = mbb.copy()
            proxy["sport"] = sport
            roster_parts.append(proxy)

    if not roster_parts:
        raise RuntimeError("Could not fetch any D1 team rosters from NCAA API.")

    roster = pd.concat(roster_parts, ignore_index=True)
    roster = roster.drop_duplicates(subset=["team", "sport"], keep="first")

    roster["popularity_score"] = roster.apply(
        lambda row: score_team(str(row["conference"]), str(row["sport"]), float(row["win_pct"])),
        axis=1,
    )
    roster["market_size_millions"] = 1.0

    # Apply higher-priority sources last so they win: benchmark < override < workbook.
    priority_frames: list[pd.DataFrame] = []
    manual = _load_manual_scores(root)
    if not manual.empty:
        benchmarks = manual[manual["source"] == "benchmark"]
        overrides = manual[manual["source"] == "override"]
        if not benchmarks.empty:
            priority_frames.append(benchmarks)
        if not overrides.empty:
            priority_frames.append(overrides)
    if games is not None and not games.empty:
        conf_lookup = {
            (str(row["team"]), str(row["sport"])): str(row["conference"])
            for _, row in roster.iterrows()
        }
        priority_frames.append(observed_scores_from_games(games, team_conferences=conf_lookup))

    for frame in priority_frames:
        if frame.empty:
            continue
        for _, row in frame.iterrows():
            mask = (roster["team"] == row["team"]) & (roster["sport"] == row["sport"])
            if mask.any():
                roster.loc[mask, "popularity_score"] = float(row["popularity_score"])
                if "conference" in row and pd.notna(row.get("conference")):
                    roster.loc[mask, "conference"] = row["conference"]
            else:
                roster = pd.concat(
                    [
                        roster,
                        pd.DataFrame(
                            [
                                {
                                    "team": row["team"],
                                    "conference": row.get("conference", "Unknown"),
                                    "win_pct": 0.5,
                                    "sport": row["sport"],
                                    "popularity_score": float(row["popularity_score"]),
                                    "market_size_millions": 1.0,
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )

    roster = roster.drop_duplicates(subset=["team", "sport"], keep="last")
    return roster[["team", "conference", "popularity_score", "market_size_millions", "sport"]].sort_values(
        ["sport", "team"]
    )


def save_d1_teams(
    output: Path | str,
    sports: list[str],
    games: pd.DataFrame | None = None,
    root: Path | str | None = None,
) -> pd.DataFrame:
    teams = build_d1_teams(sports, games=games, root=root)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    teams.to_csv(output, index=False)
    return teams
