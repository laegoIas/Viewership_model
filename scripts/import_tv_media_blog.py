"""Fetch and clean TV Media Blog viewership data for research import."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from viewership_model.data.load import load_config
from viewership_model.data.tv_media_blog_import import (
    DEFAULT_CFB_ARTICLE_URL,
    DEFAULT_MBB_ARTICLE_URL,
    save_tv_media_blog_games,
)


def _import_one(label: str, output: Path, article_url: str, sport: str) -> None:
    games = save_tv_media_blog_games(
        output,
        article_url,
        default_sport=sport,
        season=2025,
    )
    postseason = int((games["game_type"] == "postseason").sum()) if "game_type" in games.columns else 0

    print(f"{label}: wrote {len(games)} games to {output}")
    print(f"  Postseason tagged: {postseason}")
    if not games.empty:
        print("  Top 5 by viewership:")
        sample = games.nlargest(5, "viewership_millions")[
            ["sport", "away_team", "home_team", "network", "viewership_millions", "notes"]
        ]
        print(sample.to_string(index=False))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import TV Media Blog viewership CSVs")
    parser.add_argument(
        "--sport",
        choices=["all", "mbb", "football"],
        default="all",
        help="Which article(s) to import (default: all)",
    )
    args = parser.parse_args()

    config = load_config(ROOT / "config.yaml")
    paths = config["paths"]

    if args.sport in ("all", "mbb"):
        _import_one(
            "Men's basketball",
            ROOT / paths.get("research_tv_media_blog_mbb", paths.get("research_tv_media_blog", "data/research/tv_media_blog_mbb_2025.csv")),
            DEFAULT_MBB_ARTICLE_URL,
            "mens_basketball",
        )

    if args.sport in ("all", "football"):
        _import_one(
            "Football",
            ROOT / paths.get(
                "research_tv_media_blog_football",
                "data/research/tv_media_blog_cfb_2025.csv",
            ),
            DEFAULT_CFB_ARTICLE_URL,
            "football",
        )


if __name__ == "__main__":
    main()
