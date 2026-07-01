from __future__ import annotations

import csv
import io
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from viewership_model.data.d1_teams import normalize_team_name
from viewership_model.data.key_tab_import import canonicalize_network_name
from viewership_model.data.research_import import classify_game_type, normalize_research_games

DEFAULT_MBB_ARTICLE_URL = (
    "https://tvmediablog.substack.com/p/2025-26-college-basketball-viewership"
)
DEFAULT_CFB_ARTICLE_URL = (
    "https://tvmediablog.substack.com/p/2025-college-football-viewership"
)
DEFAULT_ARTICLE_URL = DEFAULT_MBB_ARTICLE_URL
DATAWRAPPER_CSV_URL = "https://datawrapper.dwcdn.net/{chart_id}/1/dataset.csv"

RESEARCH_COLUMNS = [
    "sport",
    "home_team",
    "away_team",
    "network",
    "viewership_millions",
    "season",
    "is_estimate",
    "source",
    "notes",
    "is_rivalry",
    "is_ranked_matchup",
    "is_prime_time",
    "conference",
    "game_type",
]

NETWORK_ALIASES: dict[str, str] = {
    "the cw": "CW",
    "cbs sports network": "CBSSN",
    "cbs sports": "CBSSN",
    "big ten network": "BTN",
    "sec network": "SEC Network",
    "acc network": "ACC Network",
    "usa": "USA",
    "cnbc": "CNBC",
}

MATCHUP_PREFIX = re.compile(
    r"^(?:b10|big ten|acc|b12|big 12|sec|aac|a10|atlantic 10|"
    r"pac-12|big east|mvc|wcc|mountain west|conference)\s+"
    r"(?:champ(?:ionship)?|sf|qf|semifinal|quarterfinal|final four|"
    r"second round|elite 8|sweet 16|first four|1r|2r|3r)\s*:\s*",
    re.IGNORECASE,
)
POSTSEASON_NOTE = re.compile(
    r"march madness|sweet 16|elite 8|final four|first four|second round|"
    r"conference champ|tournament|\b1r\b|\b2r\b|\b3r\b|\bqf\b|\bsf\b|"
    r"\bcfp\b|playoff|bowl\b|championship",
    re.IGNORECASE,
)
RANKING_PREFIX = re.compile(r"^#\d+\s+")
VIEWERSHIP_NUMBER = re.compile(r"([\d,]+(?:\.\d+)?)")
WOMENS_SUFFIX = re.compile(r"\s*\(W\)\s*$", re.IGNORECASE)
SKIP_MATCHUP = re.compile(r"^unavailable", re.IGNORECASE)


def _fetch_text(url: str) -> str:
    try:
        raw = subprocess.check_output(
            ["/usr/bin/curl", "-sL", "--max-time", "30", url],
            stderr=subprocess.DEVNULL,
        )
        return raw.decode("utf-8", errors="replace")
    except (subprocess.CalledProcessError, FileNotFoundError):
        with urllib.request.urlopen(url, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")


def fetch_chart_ids(article_url: str = DEFAULT_ARTICLE_URL) -> list[str]:
    html = _fetch_text(article_url)
    ids = re.findall(r"datawrapper\.dwcdn\.net/([A-Za-z0-9]+)/1/", html)
    seen: set[str] = set()
    ordered: list[str] = []
    for chart_id in ids:
        if chart_id not in seen:
            seen.add(chart_id)
            ordered.append(chart_id)
    return ordered


def fetch_chart_csv(chart_id: str) -> str:
    return _fetch_text(DATAWRAPPER_CSV_URL.format(chart_id=chart_id))


def _normalize_network(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if "+" in text:
        text = text.split("+")[0].strip()
    lowered = text.lower()
    if lowered in NETWORK_ALIASES:
        text = NETWORK_ALIASES[lowered]
    return canonicalize_network_name(text)


def _parse_viewers_thousands(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = VIEWERSHIP_NUMBER.search(text)
    if not match:
        return None
    viewers = float(match.group(1).replace(",", ""))
    return viewers if viewers > 0 else None


def _pick_viewers(panel: str | None, big_data: str | None) -> float | None:
    panel_val = _parse_viewers_thousands(panel)
    if panel_val is not None:
        return panel_val
    return _parse_viewers_thousands(big_data)


def _strip_event_prefix(matchup: str) -> str:
    text = str(matchup).strip()
    if ":" in text:
        candidate = text.rsplit(":", 1)[-1].strip()
        if "/" in candidate:
            return candidate
    return text


def _parse_matchup(matchup: str, default_sport: str = "mens_basketball") -> tuple[str, str, str, str]:
    text = _strip_event_prefix(matchup)
    text = MATCHUP_PREFIX.sub("", text)
    sport = default_sport
    if WOMENS_SUFFIX.search(text):
        sport = "womens_basketball"
        text = WOMENS_SUFFIX.sub("", text).strip()
    if "/" not in text:
        raise ValueError(f"Unrecognized matchup: {matchup!r}")
    away_raw, home_raw = text.split("/", 1)
    away = normalize_team_name(RANKING_PREFIX.sub("", away_raw.strip()))
    home = normalize_team_name(RANKING_PREFIX.sub("", home_raw.strip()))
    return sport, away, home, text


def _header_index(header: list[str]) -> dict[str, int]:
    return {name.strip().lower(): idx for idx, name in enumerate(header)}


def _cell(row: list[str], header: dict[str, int], *names: str) -> str | None:
    for name in names:
        idx = header.get(name.lower())
        if idx is None or idx >= len(row):
            continue
        value = row[idx].strip()
        if value:
            return value
    return None


def _parse_chart_rows(
    csv_text: str,
    chart_id: str,
    *,
    default_sport: str = "mens_basketball",
    season: int = 2025,
) -> list[dict]:
    reader = csv.reader(io.StringIO(csv_text))
    try:
        header = next(reader)
    except StopIteration:
        return []

    header_map = _header_index(header)
    rows: list[dict] = []

    for row in reader:
        matchup = _cell(row, header_map, "matchup", "matchup ")
        if not matchup or SKIP_MATCHUP.search(matchup):
            continue

        try:
            sport, away_team, home_team, clean_matchup = _parse_matchup(matchup, default_sport)
        except ValueError:
            continue

        event_label = ""
        if ":" in str(matchup):
            prefix_part = str(matchup).rsplit(":", 1)[0].strip()
            if "/" not in prefix_part:
                event_label = prefix_part

        network_raw = _cell(row, header_map, "network", "network(s)", "network(s) ")
        network = _normalize_network(network_raw)
        if not network:
            continue

        panel = _cell(
            row,
            header_map,
            "nielsen panel viewership (000s)",
            "nielsen panel viewership (000s) ",
        )
        big_data = _cell(
            row,
            header_map,
            "nielsen big data viewership (000s)",
            "nielsen big data viewership (000s) ",
        )
        viewers_k = _pick_viewers(panel, big_data)
        if viewers_k is None:
            continue

        tournament = _cell(row, header_map, "tournament")
        round_name = _cell(row, header_map, "round")
        date = _cell(row, header_map, "date")
        dow = _cell(row, header_map, "dow")
        start = _cell(row, header_map, "start (et)")

        note_parts = [f"TV Media Blog chart {chart_id}"]
        if event_label:
            note_parts.append(event_label)
        if tournament:
            note_parts.append(tournament)
        if round_name:
            note_parts.append(round_name)
        if date:
            note_parts.append(date)
        if dow and start:
            note_parts.append(f"{dow} {start} ET")
        elif dow:
            note_parts.append(dow)
        notes = "; ".join(note_parts)

        game_type = classify_game_type(
            sport=sport,
            notes=notes,
            network=network,
            viewership_millions=viewers_k / 1000.0,
        )
        if tournament or round_name or POSTSEASON_NOTE.search(notes):
            game_type = "postseason"

        rows.append(
            {
                "sport": sport,
                "home_team": home_team,
                "away_team": away_team,
                "network": network,
                "viewership_millions": round(viewers_k / 1000.0, 6),
                "season": season,
                "is_estimate": 0,
                "source": "TV Media Blog",
                "notes": notes,
                "is_rivalry": 0,
                "is_ranked_matchup": int("#" in matchup),
                "is_prime_time": int(bool(start and "PM" in start.upper() and any(h in start for h in ("7", "8", "9")))),
                "conference": "Unknown",
                "game_type": game_type,
                "chart_id": chart_id,
                "matchup": clean_matchup,
            }
        )
    return rows


def _dedupe_key(sport: str, home_team: str, away_team: str, network: str) -> tuple:
    teams = tuple(sorted([home_team.lower(), away_team.lower()]))
    return sport, teams, network.lower()


def import_tv_media_blog(
    article_url: str,
    *,
    default_sport: str = "mens_basketball",
    season: int = 2025,
    chart_ids: list[str] | None = None,
) -> pd.DataFrame:
    chart_ids = chart_ids or fetch_chart_ids(article_url)
    if not chart_ids:
        raise ValueError(f"No Datawrapper charts found at {article_url}")

    merged: dict[tuple, dict] = {}
    for chart_id in chart_ids:
        csv_text = fetch_chart_csv(chart_id)
        for row in _parse_chart_rows(
            csv_text,
            chart_id,
            default_sport=default_sport,
            season=season,
        ):
            key = _dedupe_key(row["sport"], row["home_team"], row["away_team"], row["network"])
            existing = merged.get(key)
            if existing is None or row["viewership_millions"] > existing["viewership_millions"]:
                merged[key] = row

    if not merged:
        return pd.DataFrame(columns=RESEARCH_COLUMNS)

    df = pd.DataFrame(merged.values())
    df = df.drop(columns=["chart_id", "matchup"], errors="ignore")
    return df.sort_values(
        ["sport", "viewership_millions", "home_team", "away_team"],
        ascending=[True, False, True, True],
    ).reset_index(drop=True)


def import_tv_media_blog_mbb(
    article_url: str = DEFAULT_MBB_ARTICLE_URL,
    chart_ids: list[str] | None = None,
) -> pd.DataFrame:
    return import_tv_media_blog(
        article_url,
        default_sport="mens_basketball",
        season=2025,
        chart_ids=chart_ids,
    )


def import_tv_media_blog_football(
    article_url: str = DEFAULT_CFB_ARTICLE_URL,
    chart_ids: list[str] | None = None,
) -> pd.DataFrame:
    return import_tv_media_blog(
        article_url,
        default_sport="football",
        season=2025,
        chart_ids=chart_ids,
    )


def save_tv_media_blog_games(
    output_path: Path | str,
    article_url: str = DEFAULT_MBB_ARTICLE_URL,
    *,
    default_sport: str = "mens_basketball",
    season: int = 2025,
) -> pd.DataFrame:
    df = import_tv_media_blog(
        article_url,
        default_sport=default_sport,
        season=season,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return df
