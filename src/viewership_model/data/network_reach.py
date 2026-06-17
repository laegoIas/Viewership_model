from __future__ import annotations

import pandas as pd

# Streaming / niche platforms anchor the bottom of the reach scale per sport.
STREAMING_NETWORKS = frozenset(
    {
        "espn+",
        "peacock",
        "focollege",
        "flo college",
        "nec front row",
        "astros.com",
        "pac-12 network",
    }
)

STREAMING_BASELINE_SCORE = 10.0
DEFAULT_BASELINE_SCORE = 25.0


def compute_network_reach_scores(sport_games: pd.DataFrame, sport: str) -> list[dict]:
    """Score networks relative to streaming baseline so cable amplifies above ESPN+."""
    streaming = sport_games[
        sport_games["network"].astype(str).str.strip().str.lower().isin(STREAMING_NETWORKS)
    ]
    if not streaming.empty:
        baseline_avg = float(streaming["avg_viewers"].median())
        baseline_score = STREAMING_BASELINE_SCORE
    else:
        baseline_avg = float(sport_games["avg_viewers"].median())
        baseline_score = DEFAULT_BASELINE_SCORE

    rows: list[dict] = []
    for network, group in sport_games.groupby("network"):
        net_key = str(network).strip().lower()
        avg_viewers = float(group["avg_viewers"].mean())
        if net_key in STREAMING_NETWORKS:
            reach = baseline_score
        else:
            ratio = avg_viewers / max(baseline_avg, 1)
            reach = min(95, max(baseline_score, baseline_score * ratio**0.38))
        rows.append(
            {
                "network": network,
                "reach_score": round(reach, 1),
                "sport": sport,
            }
        )
    return rows
