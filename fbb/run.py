"""Rebuild the waiver-wire report.

    python -m fbb.run              # uses players.csv, config.json, notes.json
    python -m fbb.run --date 2026-11-14
Writes out/report.html and out/analysis.csv.
"""
import argparse, csv, json, sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
from . import fetch, model

ROOT = Path(__file__).resolve().parent.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="report date (YYYY-MM-DD), default today in US Eastern time")
    args = ap.parse_args()
    today = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("America/New_York")).date()
    cfg = json.loads((ROOT / "config.json").read_text())
    notes = json.loads((ROOT / "notes.json").read_text()) if (ROOT / "notes.json").exists() else {}
    players = list(csv.DictReader(open(ROOT / "players.csv", encoding="utf-8")))
    delay, season = cfg["request_delay_seconds"], cfg["season"]

    pages = fetch.league_pages(season, delay)
    pg, adv, prev = model.table(pages["pg"], "per_game_stats"), model.table(pages["adv"], "advanced"), model.table(pages["prev"], "per_game_stats")
    ids = fetch.player_ids(pages["pg"])

    week_end = today + timedelta(days=6 - today.weekday())          # fantasy week runs Mon-Sun
    next_start, next_end = week_end + timedelta(days=1), week_end + timedelta(days=7)
    months = list(dict.fromkeys(d.strftime("%B").lower() for d in (today, next_end)))
    sch = model.schedule_frame([fetch.schedule(season, m, delay) for m in months])
    ts = lambda d: pd.Timestamp(d)

    rows, logs, missing = [], {}, []
    for p in players:
        name, pid = fetch.resolve(p["name"].strip(), ids)
        if not pid:
            missing.append(p["name"]); continue
        print(f"  {name}", file=sys.stderr)
        row, log = model.player(name, fetch.gamelog(pid, season, delay), pg, adv, prev, cfg, sch,
                                ts(today), ts(week_end), ts(next_start), ts(next_end))
        if row is None:
            missing.append(p["name"] + " (no games played)"); continue
        row["YAHOO"] = float(p["yahoo_proj"]) if p.get("yahoo_proj") else None
        rows.append(row); logs[name] = log

    df = model.finish(rows, cfg)
    out = ROOT / "out"; out.mkdir(exist_ok=True)
    df.to_csv(out / "analysis.csv", index=False)
    data = json.loads(df.to_json(orient="records"))
    for d in data:
        d["log"] = logs[d["player"]]
    meta = {"date": today.isoformat(), "date_label": today.strftime("%b %-d, %Y"), "count": len(data),
            "stats_through": max(g["date"] for l in logs.values() for g in l),
            "week": f"{today.strftime('%a')}–Sun", "missing": missing}
    html = (ROOT / "fbb" / "template.html").read_text()
    for key, val in (("__DATA__", data), ("__NOTES__", notes), ("__META__", meta)):
        html = html.replace(key, json.dumps(val, ensure_ascii=False))
    (out / "report.html").write_text(html)
    print(df[["player", "team", "PROJ", "FPPG", "FP3", "MIN3", "ROS_TOTAL", "wk_left", "next_wk", "last_status"]].to_string(index=False))
    if missing:
        print("\nNot found on Basketball-Reference (check spelling in players.csv):", ", ".join(missing))
    print(f"\nWrote {out / 'report.html'}")


if __name__ == "__main__":
    main()
