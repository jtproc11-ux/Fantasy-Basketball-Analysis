"""Fantasy-point projections and trend metrics."""
import io
import pandas as pd

TEAM = {'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BRK': 'Brooklyn Nets', 'CHO': 'Charlotte Hornets',
        'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers', 'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets',
        'DET': 'Detroit Pistons', 'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
        'LAC': 'Los Angeles Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies', 'MIA': 'Miami Heat',
        'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves', 'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks',
        'OKC': 'Oklahoma City Thunder', 'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHO': 'Phoenix Suns',
        'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs', 'TOR': 'Toronto Raptors',
        'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'}


def table(html, table_id):
    t = pd.read_html(io.StringIO(html), attrs={"id": table_id})[0]
    return t[t["Player"] != "Player"]


def schedule_frame(htmls):
    s = pd.concat([pd.read_html(io.StringIO(h), attrs={"id": "schedule"})[0] for h in htmls])
    s["d"] = pd.to_datetime(s["Date"], format="%a, %b %d, %Y")
    return s


def team_games(sch, team, start, end):
    full = TEAM.get(team)
    s = sch[(sch.d >= start) & (sch.d <= end)]
    return int(((s["Visitor/Neutral"] == full) | (s["Home/Neutral"] == full)).sum())


def _row(t, name):
    r = t[t.Player == name]
    if len(r) > 1:
        tot = r[r.Team.astype(str).str.match(r"\d+TM")]
        r = tot if len(tot) else r.iloc[[0]]
    return r.iloc[0] if len(r) else None


def _current_team(t, name):
    r = t[(t.Player == name) & ~t.Team.astype(str).str.match(r"\d+TM")]
    return r.iloc[-1].Team if len(r) else None


def player(name, gl_html, pg, adv, prev, cfg, sch, today, week_end, next_start, next_end):
    W = cfg["scoring"]
    fp = lambda d: sum(pd.to_numeric(d[k], errors="coerce").fillna(0) * v for k, v in W.items())
    g = [t for t in pd.read_html(io.StringIO(gl_html)) if "Gtm" in t.columns][-1]
    g = g[pd.to_numeric(g["Gtm"], errors="coerce").notna()].copy()
    played = g[g["MP"].astype(str).str.contains(":")].copy()
    if played.empty:
        return None, []
    played["min"] = played["MP"].str.split(":").apply(lambda x: int(x[0]) + int(x[1]) / 60)
    played["FP"] = fp(played)
    played["GS"] = played["GS"].astype(str).eq("*") if "GS" in played else False
    log = [dict(date=d, fp=round(f, 1), min=round(m, 1), gs=bool(s))
           for d, f, m, s in zip(played.Date, played.FP, played["min"], played.GS)]
    s, a, p = _row(pg, name), _row(adv, name), _row(prev, name)
    team = _current_team(pg, name) or s.Team
    l3, l5 = played.tail(3), played.tail(5)
    early = played.iloc[:-3] if len(played) > 3 else played.iloc[:0]
    mins = played["min"].sum()
    rate = played.FP.sum() / mins
    rate5 = l5.FP.sum() / l5["min"].sum()
    prior = cfg["fallback_rate"]
    if p is not None and float(p.MP) > 0:
        prior = sum(float(p[k]) * v for k, v in W.items()) / float(p.MP)
    k = cfg["prior_minutes"]
    proj_rate = 0.8 * (rate * mins + prior * k) / (mins + k) + 0.2 * rate5
    proj_min = 0.5 * l3["min"].mean() + 0.2 * l5["min"].mean() + 0.3 * played["min"].mean()
    num = lambda x: None if pd.isna(x) else float(x)
    return dict(
        player=name, team=team, pos=s.Pos, G=len(played), missed=len(g) - len(played),
        MPG=round(played["min"].mean(), 1), MIN3=round(l3["min"].mean(), 1),
        MIN_EARLY=round(early["min"].mean(), 1) if len(early) else None,
        FPPG=round(played.FP.mean(), 1), FP3=round(l3.FP.mean(), 1),
        FP_EARLY=round(early.FP.mean(), 1) if len(early) else None,
        FP36=round(rate * 36, 1), GS3=int(l3.GS.sum()),
        PER=num(a.PER), TS=num(a["TS%"]), USG=num(a["USG%"]), BPM=num(a.BPM),
        PROJ=round(proj_rate * proj_min, 1), PROJ_MIN=round(proj_min, 1),
        team_left=82 - int(pd.to_numeric(g["Gtm"]).max()),
        wk_left=team_games(sch, team, today, week_end), next_wk=team_games(sch, team, next_start, next_end),
        last_game=str(g.Date.iloc[-1]), last_status=str(g.MP.iloc[-1]) if ":" not in str(g.MP.iloc[-1]) else "Played",
    ), log


def finish(rows, cfg):
    df = pd.DataFrame(rows)
    df["MIN_RISE"] = (df.MIN3 - df.MIN_EARLY).round(1)
    df["FP_RISE"] = (df.FP3 - df.FP_EARLY).round(1)
    by_status = df.get("status", pd.Series("", index=df.index)).map(cfg.get("status_availability", {}))
    df["AVAIL"] = df.player.map(cfg.get("availability", {})).fillna(by_status).fillna(cfg["default_availability"])
    df["ROS_TOTAL"] = (df.PROJ * df.team_left * df.AVAIL).round(0)
    return df.sort_values("ROS_TOTAL", ascending=False)
