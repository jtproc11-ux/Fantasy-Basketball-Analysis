# Fantasy Basketball Analysis

Waiver-wire scouting for a Yahoo head-to-head **points** league. It ranks free agents by projected
fantasy points for the rest of the season and flags players whose role is growing.

Stats come from Basketball-Reference (box scores, advanced metrics, schedule). The free agent list,
injury tags and % rostered come from the league's **public** Yahoo page (league 108404), which works
without a login only while the league setting "Make League Publicly Viewable" is Yes. No Yahoo
API app or password is involved.

## Daily routine

1. Ask Claude to "update my waiver report" (in a session on this repo with the
   "Fantasy basketball" environment).
2. Claude runs `python -m fbb.run`, which reads the top 75 available players from Yahoo and fresh
   stats from Basketball-Reference, checks injury news, updates `notes.json` with the
   recommendations, and republishes the report to the same link:
   https://claude.ai/artifact/RWkhxT1CQFUZCmi6rawck7
3. Optional: send a screenshot of your roster for add/drop suggestions.

If the Yahoo page can't be read (league made private, site change), the run falls back to the
names in `players.csv`, so screenshots still work.

## Files

| File | What it holds |
|---|---|
| `players.csv` | Fallback player list, and Yahoo "Proj Pts" from screenshots (optional). |
| `config.json` | League ID, scoring, model settings, and availability discounts for injured players. |
| `fbb/yahoo_public.py` | Reads the free agent table from the public Yahoo league page (a few page loads a day). |
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

Cloud sessions need network access to `www.basketball-reference.com` and
`basketball.fantasysports.yahoo.com` (the "Fantasy basketball" environment allows both).

## How the projection works

- **Points per minute:** this season's rate, blended with last season's (worth 150 minutes of
  evidence), plus a 20% nudge toward the last 5 games.
- **Minutes:** 50% last 3 games, 20% last 5, 30% season.
- **Projected FP/G** = points per minute × minutes.
- **Rest-of-season total** = FP/G × team games left × expected availability (92% by default,
  85% when Yahoo marks a player Out, and custom values in `config.json` for long injuries).
- The report shows the top 40 by rest-of-season total, plus any player with a written recommendation.
