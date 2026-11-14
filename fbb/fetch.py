"""Download and cache Basketball-Reference pages (polite: one request every few seconds)."""
import re, subprocess, time, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
BBREF = "https://www.basketball-reference.com"
_last = [0.0]


def _get(url, dest, delay, max_age_hours=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000:
        if max_age_hours is None or time.time() - dest.stat().st_mtime < max_age_hours * 3600:
            return dest.read_text()
    wait = delay - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    r = subprocess.run(["curl", "-s", "-w", "%{http_code}", "--max-time", "40", "-o", str(dest), url],
                       capture_output=True, text=True)
    _last[0] = time.time()
    if r.stdout.strip() != "200":
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"{url} returned HTTP {r.stdout.strip()}")
    return dest.read_text()


def league_pages(season, delay, max_age_hours=6):
    """Per-game and advanced tables for this season, per-game for last season."""
    return {
        "pg": _get(f"{BBREF}/leagues/NBA_{season}_per_game.html", CACHE / f"pg_{season}.html", delay, max_age_hours),
        "adv": _get(f"{BBREF}/leagues/NBA_{season}_advanced.html", CACHE / f"adv_{season}.html", delay, max_age_hours),
        "prev": _get(f"{BBREF}/leagues/NBA_{season-1}_per_game.html", CACHE / f"pg_{season-1}.html", delay),
    }


def schedule(season, month, delay):
    return _get(f"{BBREF}/leagues/NBA_{season}_games-{month}.html", CACHE / f"sched_{season}_{month}.html", delay, 24)


def gamelog(pid, season, delay, max_age_hours=6):
    return _get(f"{BBREF}/players/{pid[0]}/{pid}/gamelog/{season}", CACHE / "gl" / f"{pid}_{season}.html", delay, max_age_hours)


def _fold(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().replace(".", "").replace("'", "").strip()
    return re.sub(r"\s+(jr|sr|ii|iii|iv)$", "", s)


def player_ids(pg_html):
    """Map player name -> Basketball-Reference id, from the per-game page."""
    ids = {}
    for pid, name in re.findall(r'data-append-csv="([a-z0-9]+)"[^>]*><a href="/players/./\1\.html">([^<]+)<', pg_html):
        ids.setdefault(name, pid)
    return ids


def resolve(name, ids):
    if name in ids:
        return name, ids[name]
    want = _fold(name)
    for n, pid in ids.items():
        if _fold(n) == want or _fold(n).startswith(want + " "):
            return n, pid
    return None, None


def player_ids_by_team(pg_html):
    """(name, team) -> id, so two players with the same name can be told apart."""
    out = {}
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', pg_html, re.S):
        m = re.search(r'data-append-csv="([a-z0-9]+)"[^>]*><a href="/players/./\1\.html">([^<]+)<', row)
        t = re.search(r'data-stat="team_name_abbr"[^>]*>(?:<a[^>]*>)?([A-Z0-9]+)', row)
        if m and t:
            out[(_fold(m.group(2)), t.group(1))] = (m.group(2), m.group(1))
    return out


YAHOO_TO_BBREF = {"BKN": "BRK", "PHX": "PHO", "CHA": "CHO", "GS": "GSW", "NY": "NYK", "NO": "NOP", "SA": "SAS",
                  "UTAH": "UTA", "WSH": "WAS"}


def resolve_with_team(name, yahoo_team, ids, by_team):
    team = YAHOO_TO_BBREF.get(yahoo_team, yahoo_team)
    hit = by_team.get((_fold(name), team))
    return hit if hit else resolve(name, ids)
