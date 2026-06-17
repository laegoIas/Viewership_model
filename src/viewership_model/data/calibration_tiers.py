from __future__ import annotations

import numpy as np
import pandas as pd

# Median viewership (millions) from Arizona spreadsheet — anchors "typical" schedule games.
SPREADSHEET_MEDIAN_MILLIONS: dict[str, float] = {
    "baseball": 0.0105,
    "softball": 0.0092,
    "football": 0.3738,
    "mens_basketball": 0.625,
    "womens_basketball": 0.0045,
}

MARQUEE_VIEWERSHIP_MILLIONS: dict[str, float] = {
    "football": 4.0,
    "mens_basketball": 1.2,
    "womens_basketball": 0.8,
    "softball": 0.10,
    "baseball": 0.08,
}

MARQUEE_MULTIPLIER = 3.0


def _is_research_row(source_sheet: str) -> bool:
    return str(source_sheet).startswith("research:")


def assign_calibration_tier(df: pd.DataFrame) -> pd.Series:
    """Label games typical (schedule) vs marquee (top-rated article outliers)."""
    tiers: list[str] = []
    spreadsheet_medians: dict[str, float] = {}

    if "source_sheet" in df.columns:
        spreadsheet = df[~df["source_sheet"].astype(str).apply(_is_research_row)]
        if not spreadsheet.empty and "viewership_millions" in spreadsheet.columns:
            for sport, group in spreadsheet.groupby("sport"):
                spreadsheet_medians[str(sport)] = float(group["viewership_millions"].median())

    for sport, median in SPREADSHEET_MEDIAN_MILLIONS.items():
        spreadsheet_medians.setdefault(sport, median)

    for row in df.itertuples():
        if not _is_research_row(getattr(row, "source_sheet", "")):
            tiers.append("typical")
            continue

        sport = str(row.sport)
        viewers = float(row.viewership_millions)
        floor = MARQUEE_VIEWERSHIP_MILLIONS.get(sport, 0.5)
        anchor = spreadsheet_medians.get(sport, viewers)
        threshold = max(floor, anchor * MARQUEE_MULTIPLIER)
        tiers.append("marquee" if viewers >= threshold else "typical")

    return pd.Series(tiers, index=df.index)


def compute_calibration_weights(df: pd.DataFrame, config: dict) -> np.ndarray:
    """Downweight research marquee games and estimates so schedule data drives scale."""
    training = config.get("training", {})
    weights_cfg = training.get("weights", {})

    spreadsheet_w = float(weights_cfg.get("spreadsheet", 1.0))
    research_typical_w = float(weights_cfg.get("research_typical", 0.5))
    research_marquee_w = float(weights_cfg.get("research_marquee", 0.08))
    estimate_w = float(weights_cfg.get("estimate", 0.35))

    weights = np.ones(len(df), dtype=float)
    is_estimate = df.get("is_estimate", pd.Series(0, index=df.index)).fillna(0).astype(int).values
    weights[is_estimate == 1] *= estimate_w

    source_sheet = df.get("source_sheet", pd.Series("", index=df.index)).astype(str)
    is_research = source_sheet.apply(_is_research_row).values

    tier = df.get("calibration_tier", assign_calibration_tier(df))
    is_marquee = (tier == "marquee").values

    for i in range(len(df)):
        if not is_research[i]:
            weights[i] *= spreadsheet_w
        elif is_marquee[i]:
            weights[i] *= research_marquee_w
        else:
            weights[i] *= research_typical_w

    return weights
