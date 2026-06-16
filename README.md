# College Athletics Viewership Model

Estimate game viewership from **team popularity** and **network reach** scales.

## How it works

```
viewers = sport_scale x (network_reach / 100) x (combined_team_popularity / 100)
```

- **Team scale** (`data/teams.csv` + `data/team_overrides.csv`): each team rated 0–100 per sport
- **Network scale** (`data/networks.csv` + `data/network_overrides.csv`): each network rated 0–100 per sport
- **Sport scale**: calibrated from your Arizona spreadsheet when you run `train.py` (yellow cells weighted lower)

Your Excel file is **training data** to calibrate the scales — not a lookup table.

## Quick start

```bash
pip install -r requirements.txt
py scripts/import_arizona.py
py scripts/train.py
py scripts/ask.py "njit mens basketball versus villanova on fs1"
```

If network (or sport) is missing, `ask` will prompt you.

## Tune the scales

Team and network ratings are **per sport**. Duke can be 95 in men's basketball and 52 in football.

| File | Purpose |
|------|---------|
| `data/team_overrides.csv` | Popularity 0–100 per **team + sport** (e.g. `Duke,mens_basketball,95` and `Duke,football,52`) |
| `data/network_overrides.csv` | Reach 0–100 per **network + sport** (e.g. FS1 men's basketball vs FS1 football) |

Auto-imported scores in `data/teams.csv` only reflect how games in your Arizona sheet performed. Use overrides for national brands or teams not in that sheet.

Higher team popularity or network reach = higher estimated viewership.

## Project layout

```
data/teams.csv, networks.csv       # auto-built from Arizona import
data/team_overrides.csv              # manual team popularity edits
data/network_overrides.csv           # manual network reach edits
src/viewership_model/models/scoring.py
scripts/ask.py                       # plain-English estimates
scripts/train.py                     # calibrate sport scales from spreadsheet
```
