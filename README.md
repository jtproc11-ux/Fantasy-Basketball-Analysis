# Fantasy Basketball Analysis

Waiver-wire scouting for a Yahoo head-to-head **points** league. It ranks free agents by projected
fantasy points for the rest of the season and flags players whose role is growing.

Stats come from Basketball-Reference (box scores, advanced metrics, schedule). Yahoo isn't
connected; the free agent list comes from screenshots of the Yahoo app.

## Daily routine

1. Send Claude screenshots of Yahoo's **Players** tab (Available players), plus your roster if you
   want add/drop suggestions.
2. Claude updates `players.csv` with the players in the screenshots, runs `python -m fbb.run`,
   reviews the results and the news, updates `notes.json` with the recommendations, and republishes
   the report to the same link.

## Files

| File | What it holds |
|---|---|
| `players.csv` | Players to analyze. `yahoo_proj` is Yahoo's "Proj Pts" when the screenshot shows it (optional). |
| `config.json` | League scoring, model settings, and availability discounts for injured players. |
| `notes.json` | The written recommendations: tier for each player and the pick cards at the top of the report. |
| `fbb/fetch.py` | Downloads and caches Basketball-Reference pages, one request every 4 seconds. |
| `fbb/model.py` | Fantasy points, trends and projections. |
| `fbb/run.py` | Builds `out/report.html` and `out/analysis.csv`. |
| `fbb/template.html` | The report page and its charts. |

## Running it

```bash
pip install -r requirements.txt
python -m fbb.run                 # today's date in US Eastern time
python -m fbb.run --date 2026-11-14
```

Cloud sessions need network access to `www.basketball-reference.com` (the "Fantasy basketball"
environment allows it).

## How the projection works

- **Points per minute:** this season's rate, blended with last season's (worth 150 minutes of
  evidence), plus a 20% nudge toward the last 5 games.
- **Minutes:** 50% last 3 games, 20% last 5, 30% season.
- **Projected FP/G** = points per minute × minutes.
- **Rest-of-season total** = FP/G × team games left × expected availability (92% by default,
  lower for injured players in `config.json`).
