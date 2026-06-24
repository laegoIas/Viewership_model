from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from viewership_model.data.calibration_tiers import tag_marquee_games

RESEARCH_GAME_COLUMNS = {
    "sport",
    "home_team",
    "away_team",
    "network",
    "viewership_millions",
}

BENCHMARK_GAME_METRICS = {"reported_game", "game_viewers"}

POSTSEASON_PATTERN = re.compile(
    r"cfp|playoff|bowl game|national championship|first round|semifinal|quarterfinal|"
    r"orange bowl|cotton bowl|rose bowl|peach bowl|sugar bowl|fiesta bowl|"
    r"liberty bowl|citrus bowl|gator bowl|pinstripe bowl|alamo bowl|reliaquest bowl|"
    r"pop-tarts bowl|mayo bowl|rate bowl|cactus bowl|birmingham bowl|texas bowl|"
    r"wcws|mcws|ncaa regional|\bregional\b|super regional|"
    r"sec championship|big ten championship|acc championship|big 12 championship|"
    r"mountain west championship|conference championship|"
    r"ncaa championship|tournament final|big east quarterfinal|"
    r"champ week|mcws finals|wcws finals",
    re.IGNORECASE,
)

REGULAR_SEASON_NAME_EXCEPTIONS = re.compile(
    r"iron bowl|egg bowl|army-navy|red river",
    re.IGNORECASE,
)

DEFAULT_GAME_TYPES = ("regular_season",)


def _parse_matchup_entity(entity: str) -> tuple[str, str] | None:
    """Parse 'Team A vs Team B' or 'Team A-Team B' into two team names."""
    text = str(entity).strip()
    for sep in (" vs ", " vs. ", " at ", " @ "):
        if sep in text.lower():
            parts = re.split(re.escape(sep), text, maxsplit=1, flags=re.IGNORECASE)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    if "-" in text:
        parts = text.split("-", 1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), parts[1].strip()
    return None


def _dedupe_key(sport: str, home_team: str, away_team: str, network: str) -> tuple:
    teams = tuple(sorted([home_team.strip().lower(), away_team.strip().lower()]))
    return sport.strip().lower(), teams, network.strip().lower()


def classify_game_type(
    sport: str,
    notes: str = "",
    week: int | float | None = None,
    network: str = "",
    viewership_millions: float | None = None,
) -> str:
    """Label a game regular_season or postseason from notes and heuristics."""
    text = str(notes or "")
    if REGULAR_SEASON_NAME_EXCEPTIONS.search(text):
        return "regular_season"
    if POSTSEASON_PATTERN.search(text):
        return "postseason"
    if sport == "baseball" and week is not None and float(week) >= 40:
        if str(network).strip() in {"ESPN", "ABC", "ESPNU", "ESPN2"}:
            if viewership_millions is not None and float(viewership_millions) >= 0.3:
                return "postseason"
    return "regular_season"


def filter_game_types(df: pd.DataFrame, game_types: list[str] | tuple[str, ...] | None) -> pd.DataFrame:
    if df.empty or not game_types:
        return df
    if "game_type" not in df.columns:
        return df
    return df[df["game_type"].isin(game_types)].copy()


def filter_primary_games(df: pd.DataFrame, game_types: list[str] | tuple[str, ...] | None) -> pd.DataFrame:
    """Drop postseason rows from Arizona/imported spreadsheet games."""
    if df.empty or not game_types or "regular_season" not in game_types:
        return df

    out = df.copy()
    if "game_type" not in out.columns:
        out["game_type"] = [
            classify_game_type(
                sport=str(row.sport),
                notes=str(getattr(row, "source_sheet", "")),
                week=getattr(row, "week", None),
                network=str(row.network),
                viewership_millions=float(row.viewership_millions),
            )
            for row in out.itertuples()
        ]
    return filter_game_types(out, game_types)


def load_research_games(
    path: Path | str,
    game_types: list[str] | tuple[str, ...] | None = DEFAULT_GAME_TYPES,
) -> pd.DataFrame:
    """Load supplemental game-level viewership from data/research/games.csv."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    missing = RESEARCH_GAME_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Research games file missing columns: {sorted(missing)}")
    return filter_game_types(normalize_research_games(df), game_types)


def games_from_benchmarks(
    path: Path | str,
    game_types: list[str] | tuple[str, ...] | None = DEFAULT_GAME_TYPES,
) -> pd.DataFrame:
    """Convert reported_game rows in viewership_benchmarks.csv to game records."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path)
    rows: list[dict] = []
    for record in df.itertuples():
        if getattr(record, "entity_type", None) != "game":
            continue
        if getattr(record, "metric", None) not in BENCHMARK_GAME_METRICS:
            continue
        avg_viewers = getattr(record, "avg_viewers", None)
        if pd.isna(avg_viewers):
            continue

        matchup = _parse_matchup_entity(getattr(record, "entity", ""))
        if not matchup:
            continue
        home_team, away_team = matchup
        network = getattr(record, "network", None)
        if pd.isna(network) or not str(network).strip():
            continue

        rows.append(
            {
                "sport": str(record.sport),
                "home_team": home_team,
                "away_team": away_team,
                "network": str(network).strip(),
                "viewership_millions": float(avg_viewers) / 1_000_000,
                "season": getattr(record, "season", ""),
                "is_estimate": 0,
                "source": getattr(record, "source", "viewership_benchmarks"),
                "notes": getattr(record, "notes", ""),
            }
        )

    if not rows:
        return pd.DataFrame()
    return filter_game_types(normalize_research_games(pd.DataFrame(rows)), game_types)


def normalize_research_games(df: pd.DataFrame) -> pd.DataFrame:
    """Expand research rows into the same schema as Arizona games.csv."""
    if df.empty:
        return df

    out = df.copy()
    out["viewership_millions"] = pd.to_numeric(out["viewership_millions"], errors="coerce")
    out = out[out["viewership_millions"].notna() & (out["viewership_millions"] > 0)]
    if out.empty:
        return out

    out["avg_viewers"] = out["viewership_millions"] * 1_000_000
    if "is_estimate" not in out.columns:
        out["is_estimate"] = 0
    else:
        out["is_estimate"] = out["is_estimate"].fillna(0).astype(int)
    if "season" not in out.columns:
        out["season"] = 2024
    out["season"] = pd.to_numeric(out["season"], errors="coerce").fillna(2024).astype(int)
    if "week" not in out.columns:
        out["week"] = 1
    out["week"] = pd.to_numeric(out["week"], errors="coerce").fillna(1).astype(int)
    for col, default in [
        ("conference", "Unknown"),
        ("location_type", "neutral"),
        ("location_city", "Unknown"),
        ("location_state", "ST"),
        ("source", "research"),
        ("notes", ""),
        ("gender", ""),
        ("game_date", ""),
    ]:
        if col not in out.columns:
            out[col] = default
        else:
            out[col] = out[col].fillna(default)
    for col, default in [("is_rivalry", 0), ("is_ranked_matchup", 1), ("is_prime_time", 0)]:
        if col not in out.columns:
            out[col] = default
        else:
            out[col] = out[col].fillna(default).astype(int)

    out["source_sheet"] = "research:" + out["source"].astype(str)
    out["opponent"] = out["away_team"]
    if "game_type" not in out.columns:
        out["game_type"] = [
            classify_game_type(
                sport=str(row.sport),
                notes=str(row.notes),
                week=row.week if hasattr(row, "week") else None,
                network=str(row.network),
                viewership_millions=float(row.viewership_millions),
            )
            for row in out.itertuples()
        ]
    else:
        out["game_type"] = out["game_type"].fillna("regular_season")

    out = out.reset_index(drop=True)
    out["game_id"] = [
        f"RS-{row.sport}-{int(row.season)}-{idx:04d}"
        for idx, row in enumerate(out.itertuples(), start=1)
    ]
    return out


def merge_games(primary: pd.DataFrame, supplemental: pd.DataFrame) -> pd.DataFrame:
    """Append research games, skipping duplicates already in the primary set."""
    if supplemental.empty:
        return primary
    if primary.empty:
        return supplemental

    primary = primary.copy()
    existing = {
        _dedupe_key(str(r.sport), str(r.home_team), str(r.away_team), str(r.network))
        for r in primary.itertuples()
    }

    extra_rows = []
    for row in supplemental.itertuples():
        key = _dedupe_key(str(row.sport), str(row.home_team), str(row.away_team), str(row.network))
        if key not in existing:
            extra_rows.append(supplemental.loc[row.Index])
            existing.add(key)

    if not extra_rows:
        return primary
    return pd.concat([primary, pd.DataFrame(extra_rows)], ignore_index=True)


def load_all_games(
    games_path: Path | str,
    research_games_path: Path | str | None = None,
    benchmarks_path: Path | str | None = None,
    game_types: list[str] | tuple[str, ...] | None = DEFAULT_GAME_TYPES,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Load Arizona games plus supplemental research and benchmark game rows."""
    games_path = Path(games_path)
    primary = pd.read_csv(games_path) if games_path.exists() else pd.DataFrame()
    primary = filter_primary_games(primary, game_types)

    supplemental_parts: list[pd.DataFrame] = []
    if research_games_path and Path(research_games_path).exists():
        supplemental_parts.append(load_research_games(research_games_path, game_types))
    if benchmarks_path and Path(benchmarks_path).exists():
        supplemental_parts.append(games_from_benchmarks(benchmarks_path, game_types))

    supplemental = pd.DataFrame()
    if supplemental_parts:
        supplemental = supplemental_parts[0]
        for part in supplemental_parts[1:]:
            supplemental = merge_games(supplemental, part)

    merged = merge_games(primary, supplemental)
    if not merged.empty:
        merged = tag_marquee_games(merged)
    stats = {
        "primary_rows": len(primary),
        "supplemental_rows": len(supplemental),
        "merged_rows": len(merged),
        "added_rows": len(merged) - len(primary),
    }
    return merged, stats
