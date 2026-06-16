from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_manual_baselines(path: Path | str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        return pd.DataFrame(columns=["sport", "network", "baseline_viewers", "source"])
    return pd.read_csv(path)


def build_baselines_from_games(games: pd.DataFrame) -> pd.DataFrame:
    if games.empty:
        return pd.DataFrame(columns=["sport", "network", "baseline_viewers", "source"])

    rows: list[dict] = []
    for (sport, network), group in games.groupby(["sport", "network"]):
        reported = group[group.get("is_estimate", 0) == 0]
        source = reported if len(reported) >= 2 else group
        if len(source) < 2:
            continue
        rows.append(
            {
                "sport": sport,
                "network": network,
                "baseline_viewers": float(source["avg_viewers"].median()),
                "source": "historical",
            }
        )
    return pd.DataFrame(rows)


def merge_baselines(games: pd.DataFrame, manual_path: Path | str) -> pd.DataFrame:
    historical = build_baselines_from_games(games)
    manual = load_manual_baselines(manual_path)
    if historical.empty:
        return manual
    if manual.empty:
        return historical
    combined = pd.concat([historical, manual], ignore_index=True)
    combined = combined.sort_values("source").drop_duplicates(subset=["sport", "network"], keep="last")
    return combined


def lookup_baseline(
    baselines: pd.DataFrame,
    sport: str,
    network: str,
) -> float | None:
    if baselines.empty:
        return None
    match = baselines[(baselines["sport"] == sport) & (baselines["network"] == network)]
    if match.empty:
        return None
    return float(match.iloc[0]["baseline_viewers"])


def anchor_prediction(
    model_millions: float,
    sport: str,
    network: str,
    combined_popularity: float,
    baselines: pd.DataFrame,
    training_games: pd.DataFrame,
    uses_default_teams: bool,
    sport_avg_popularity: float = 50.0,
) -> float:
    baseline_viewers = lookup_baseline(baselines, sport, network)
    if baseline_viewers is None:
        return model_millions

    pop_multiplier = (combined_popularity / sport_avg_popularity) ** 0.35
    anchored_millions = (baseline_viewers / 1_000_000) * pop_multiplier

    if training_games.empty:
        n_games = 0
    else:
        n_games = len(
            training_games[
                (training_games["sport"] == sport) & (training_games["network"] == network)
            ]
        )

    if n_games == 0:
        return anchored_millions

    if n_games < 3 or uses_default_teams:
        anchor_weight = 0.65
    else:
        anchor_weight = 0.25

    return anchor_weight * anchored_millions + (1 - anchor_weight) * model_millions
