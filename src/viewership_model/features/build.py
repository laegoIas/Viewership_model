from __future__ import annotations

import pandas as pd

from viewership_model.models.scoring import combine_team_popularity

DEFAULT_POPULARITY = 35.0
DEFAULT_NETWORK_REACH = 40.0


def enrich_games(
    games: pd.DataFrame,
    teams: pd.DataFrame,
    networks: pd.DataFrame,
    star_weight: float = 0.65,
) -> pd.DataFrame:
    """Join reference tables and derive model features."""
    teams_ref = teams.drop_duplicates(subset=["team", "sport"])

    home = teams_ref.rename(
        columns={
            "team": "home_team",
            "popularity_score": "home_popularity",
            "market_size_millions": "home_market_size",
        }
    )[["home_team", "sport", "home_popularity", "home_market_size"]]

    away = teams_ref.rename(
        columns={
            "team": "away_team",
            "popularity_score": "away_popularity",
        }
    )[["away_team", "sport", "away_popularity"]]

    net = networks.rename(columns={"reach_score": "network_reach"})[
        ["network", "sport", "network_reach"]
    ]

    df = games.merge(home, on=["home_team", "sport"], how="left")
    df = df.merge(away, on=["away_team", "sport"], how="left")
    df = df.merge(net, on=["network", "sport"], how="left")

    df["home_used_default"] = df["home_popularity"].isna()
    df["away_used_default"] = df["away_popularity"].isna()

    df["home_popularity"] = df["home_popularity"].fillna(DEFAULT_POPULARITY)
    df["away_popularity"] = df["away_popularity"].fillna(DEFAULT_POPULARITY)
    df["home_market_size"] = df["home_market_size"].fillna(1.0)
    df["network_reach"] = df["network_reach"].fillna(DEFAULT_NETWORK_REACH)
    df["combined_popularity"] = df.apply(
        lambda row: combine_team_popularity(
            float(row["home_popularity"]),
            float(row["away_popularity"]),
            star_weight,
        ),
        axis=1,
    )
    df["neutral_site"] = (df["location_type"] == "neutral").astype(int)
    df["week_of_season"] = df["week"] if "week" in df.columns else 1

    for col in ["is_rivalry", "is_ranked_matchup", "is_prime_time"]:
        if col in df.columns:
            df[col] = df[col].astype(int)

    return df


def get_feature_columns(config: dict) -> tuple[list[str], list[str]]:
    features = config["features"]
    return features["categorical"], features["numeric"]


def build_feature_matrix(
    df: pd.DataFrame, config: dict
) -> tuple[pd.DataFrame, pd.Series | None]:
    """Return X and optional y for modeling."""
    cat_cols, num_cols = get_feature_columns(config)
    available_cat = [c for c in cat_cols if c in df.columns]
    available_num = [c for c in num_cols if c in df.columns]

    X = df[available_cat + available_num].copy()
    for col in available_cat:
        X[col] = X[col].astype(str)

    target_col = config["target"]["column"]
    y = df[target_col] if target_col in df.columns else None
    return X, y
