# Viewership research

Published benchmarks used to calibrate **team popularity** (0–100) and **network reach** (0–100) scales in this model.

## Sources

| Source | URL | Best for |
|--------|-----|----------|
| College Football Network | https://collegefootballnetwork.com/2024-college-football-tv-ratings/ | CFB network averages |
| Sports Media Watch | https://www.sportsmediawatch.com/ | Game-by-game ratings |
| Sports Business Journal | https://www.sportsbusinessjournal.com/ | Network/season trends |
| ESPN Press Room | https://espnpressroom.com/ | Softball, basketball, CFB |
| Nielsen | https://www.nielsen.com/ | Top CFB teams 2024 |
| On3 | https://www.on3.com/ | Team season averages |

## Key findings by sport

### Football (regular season, avg per game)

| Network | Avg viewers | Suggested reach /100 |
|---------|-------------|----------------------|
| ABC | ~5.4M | 100 |
| CBS | ~3.3M | 72 |
| FOX / NBC | ~3.1M | 70 |
| ESPN | ~1.7M | 52 |
| Big Ten Network | ~697K | 38 |
| ESPN2 / FS1 | ~418K | 32 |
| ESPNU | ~57K | 18 |

**Top teams (2025 avg per game):** Alabama ~8.5M, Texas/Georgia ~7.5M, Ohio State ~6.6M, Oklahoma ~6.5M.

**Not Nielsen-measured:** SEC Network, ACC Network, ESPN+, Peacock (use overrides or Arizona sheet).

### Men's basketball (regular season)

| Network | Avg viewers | Suggested reach /100 |
|---------|-------------|----------------------|
| ABC | ~1.7M | 100 |
| CBS | ~1.3–1.4M | 88 |
| FOX | ~1.0–1.2M | 78 |
| ESPN | ~1.0M | 75 |
| FS1 | ~200–234K | 28 |
| Big Ten Network | ~222K | 27 |
| ESPNU | ~85–150K | 20 |

**Example games:** NJIT vs Villanova on FS1 ~105K (verified). Marquette vs Villanova FS1 ~380K.

**Top brands:** Duke, UConn, UNC, Kentucky — marquee games 2M+ on ESPN.

### Softball

| Context | Avg viewers |
|---------|-------------|
| ESPN regular season (2026) | ~292K |
| ESPN regular season (2024) | ~190K |
| WCWS (2025) | ~1.3M |
| ESPN+ regular (Arizona vs Alabama) | ~13K |
| ESPN marquee (Alabama vs Auburn) | ~570K |

Streaming (ESPN+) is **much** lower than linear ESPN for regular-season games.

### Baseball

| Context | Avg viewers |
|---------|-------------|
| MCWS full tournament | ~1.56M |
| MCWS finals | ~2.82M |
| Regular season / ESPN+ | Highly variable; often under 50K on streaming |

## How benchmarks map to model scales

```
network_reach = 100 × (benchmark_avg / sport_top_network_avg) ^ 0.35
team_popularity = 100 × (benchmark_avg / sport_top_team_avg) ^ 0.35
```

Edit `data/network_overrides.csv` and `data/team_overrides.csv`, then run `py scripts/train.py`.

Raw data: `viewership_benchmarks.csv` and `games.csv` (game-level Nielsen/reporting).

Game-level research rows are merged into training automatically when you run `py scripts/train.py`. Preview the merge:

```bash
py scripts/import_research.py
```

Print suggested scores from benchmarks:

```bash
py scripts/research_scales.py
```
