# Research viewership sources

Supplemental game-level data lives in `data/research/games.csv` and is merged into training at `scripts/train.py` time (after valuation workbook games in `data/games.csv`). Rows in `data/viewership_benchmarks.csv` with `entity_type=game` are also converted to games automatically.

**Current scale (286 games, 114 teams):**

| Sport | Games | Reported (`is_estimate=0`) |
|-------|------:|-----------------------------:|
| Football | 120 | ~90 |
| Men's basketball | 45 | ~25 |
| Softball | 45 | ~15 |
| Baseball | 42 | ~10 |
| Women's basketball | 34 | ~25 |

---

## Primary sources (reported viewership)

### Sports Media Watch
- **URL:** https://www.sportsmediawatch.com/college-football-tv-ratings/
- **Used for:** Football (2024–25), men's basketball, women's basketball
- **Notes:** Nielsen “Big Data + Panel” figures from 2025 onward; generally higher than pre-2025 panel-only numbers. Weekly CFB recaps and MBB season summaries.

### Football Scoop
- **URL:** https://footballscoop.com (season viewership roundups)
- **Used for:** 2024 FBS regular-season football (ABC, FOX, CBS, NBC, ESPN)
- **Notes:** Large SEC/ACC/Big Ten sample; many 4M–13M games. Army–Navy and rivalry games included.

### ESPN Press Room
- **URL:** https://espnpressroom.com
- **Used for:** Men's basketball (2024–25), women's basketball, softball, some baseball
- **Notes:** Official ESPN/ABC reported audiences for marquee regular-season games.

### Statista / On3 (2025 football)
- **URLs:**
  - https://www.statista.com/statistics/616199/college-football-most-watched-games/
  - https://www.on3.com/news/college-football-tv-ratings-top-10-most-watched-games-2025-26-season-cfp/
- **Used for:** 2025 FBS regular-season top games (Ohio State–Michigan, Texas–Ohio State, etc.)

### Front Office Sports
- **URL:** https://frontofficesports.com
- **Used for:** 2025–26 men's basketball (Duke–Arkansas Thanksgiving, Duke–Michigan on ESPN)

### The Boneyard (UConn WBB forum)
- **URL:** https://theboneyard.com
- **Used for:** Women's basketball game-by-game ESPN/FOX ratings compilations
- **Notes:** Community-maintained but cross-checked against network releases.

### CSNBB
- **Used for:** Men's basketball SEC/Big 12 1M+ club games (2023–24)

### Sports Business Journal
- **URL:** https://www.sportsbusinessjournal.com
- **Used for:** Network averages (FS1, BTN, CW) and select game callouts; 2025 SMU–Baylor on CW

### Other one-off reported sources
| Source | Sport | Example |
|--------|-------|---------|
| User verified | MBB | NJIT vs Villanova, FS1 (105K) |
| Arizona spreadsheet | Baseball/softball | ESPN+ regular-season streaming from valuation workbook |
| Yahoo Sports | WBB | ABC doubleheader (UConn–South Carolina, LSU–Texas) |
| Philadelphia Inquirer | WBB | USC at UConn on FOX (~2.3M) |

---

## Estimated rows (`is_estimate=1`)

~39% of research games are **estimates**, tiered from network averages or sport/conference benchmarks when game-specific Nielsen data is unavailable (common for ESPNU, SEC Network, ACC Network, ESPN+, FloCollege).

Estimates are downweighted in training via `config.yaml`:

```yaml
training:
  weights:
    research_typical: 0.45
    estimate: 0.35
```

Use estimates for coverage and relative scale, not as exact audience guarantees.

---

## Workbook data (separate from research CSV)

School valuation workbooks (Arizona, NJIT, Monmouth) import into `data/games.csv` via `scripts/import_valuations.py`. Those rows are weighted at `spreadsheet: 1.0` and take priority for schools that own the workbook.

| School | File | Sports |
|--------|------|--------|
| Arizona | `data/Arizona Jersey Patch Valuation .xlsx` | Multi-sport |
| NJIT | `data/NJIT Jersey Patch Valuation 2024-25.xlsx` | Multi-sport |
| Monmouth | `data/Monmouth Jersey Patch Valuation.xlsx` | MBB, WBB, baseball, football |

---

## Marquee tag (`is_marquee`)

Every game is auto-tagged when loaded:

| Column | Value | Meaning |
|--------|-------|---------|
| `is_marquee` | `0` | Schedule-tier — used for training and MAE/R² |
| `is_marquee` | `1` | Marquee — Iron Bowl, Duke–UNC, 3M+ football, etc. |

Thresholds (per sport): football ≥3M viewers, men's basketball ≥1.2M, and so on. See `calibration_tiers.py`.

**Manual override:** add `is_marquee` to a row in `games.csv` or `research/games.csv` (`0` or `1`).

Training setting in `config.yaml`:

```yaml
training:
  exclude_marquee: true   # marquee rows never enter train/test split
```

Reference-only marquee lists also live in `marquee_games.csv` (not merged into training).

---

## Adding a new game

1. Add a row to `data/research/games.csv`:

```csv
sport,home_team,away_team,network,viewership_millions,season,is_estimate,source,notes,is_rivalry,is_ranked_matchup,is_prime_time,conference,is_marquee
mens_basketball,Team A,Team B,FS1,0.105,2025,0,Sports Media Watch,Regular season Feb 2025,0,1,0,Big East,
```

Optional `is_marquee` (leave blank for auto-tag, or set `0`/`1` to override).

2. `viewership_millions` = average viewers ÷ 1,000,000 (e.g. 105,000 → `0.105`).
3. Set `is_estimate=0` only when the number comes from a reported source.
4. Put the publication name in `source` and a short context string in `notes`.
5. Re-run `python3 scripts/train.py`.

---

## Networks without public Nielsen data

ESPN does not subscribe to Nielsen for **SEC Network**, **ACC Network**, **Longhorn Network**, etc. (uses ComScore internally). Public game-level ratings for those networks are rare; estimates in this file are based on cable-tier benchmarks unless a press release cites a specific game.

---

## Useful references for future expansion

- **CFB:** https://www.sportsmediawatch.com/college-football-tv-ratings/
- **MBB/WBB:** Sports Media Watch college basketball, ESPN Press Room season wraps
- **Baseball:** ESPN Press Room (postseason/regional); regular-season linear often estimated
- **Softball:** ESPN Press Room regular-season and WCWS releases
- **Network averages:** `data/research/viewership_benchmarks.csv`
