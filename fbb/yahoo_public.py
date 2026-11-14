"""Read the free agent list from a *publicly viewable* Yahoo league (no login).

Only works while the league setting "Make League Publicly Viewable" is Yes.
Kept deliberately light: one page per 25 players, a few seconds apart, about once a day.
"""
import io, re
import pandas as pd
from lxml import html as LH
from . import fetch

SITE = "https://basketball.fantasysports.yahoo.com"


def _page(league_id, offset, delay):
    url = (f"{SITE}/nba/{league_id}/players?status=A&eteam=ALL&fteam=NONE&pos=P&cut_type=33"
           f"&stat1=S_AS_2026&myteam=0&sort=AR&sdir=1&count={offset}")
    return fetch._get(url, fetch.CACHE / "yahoo" / f"fa_{league_id}_{offset}.html", delay, max_age_hours=3)


def _rows(page_html):
    doc = LH.fromstring(page_html)
    table = pd.read_html(io.StringIO(page_html))[0]
    table.columns = [c[1] if "Unnamed" not in c[1] else c[0] for c in table.columns]
    trs = [tr for tr in doc.xpath("//table")[0].xpath(".//tbody/tr")]
    out = []
    for tr, (_, r) in zip(trs, table.iterrows()):
        a = tr.xpath(".//div[contains(@class,'ysf-player-name')]//a[contains(@class,'name')]")
        if not a:
            continue
        st = tr.xpath(".//span[contains(@class,'ysf-player-status')]//span[@title]")
        tp = tr.xpath(".//span[contains(@class,'Fz-xxs') and contains(text(),' - ')]/text()")
        team, pos = (tp[0].split(" - ", 1) + [""])[:2] if tp else ("", "")
        out.append({
            "name": a[0].get("title") or a[0].text_content().strip(),
            "yahoo_id": a[0].get("data-ys-playerid"),
            "yahoo_team": team.strip(), "positions": pos.strip(),
            "status": st[0].get("title") if st else "",
            "waiver": str(r.get("Roster Status", "")),
            "yahoo_gp": r.get("GP*"), "yahoo_fp": r.get("Fan Pts"),
            "rank_now": r.get("Current", r.get("Current")), "rank_pre": r.get("Pre-Season"),
            "rostered": str(r.get("% Ros", "")),
        })
    return out


def free_agents(league_id, n=75, delay=4):
    players = []
    for off in range(0, n, 25):
        rows = _rows(_page(league_id, off, delay))
        players += rows
        if len(rows) < 25:
            break
    return players
