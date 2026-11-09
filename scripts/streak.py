#!/usr/bin/env python3
"""Generate assets/streak.svg (current streak, longest streak, total contributions)
from the GitHub GraphQL API. Standard library only."""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "Michael-Olaoluwa")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT", "assets/streak.svg")

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    createdAt
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


def gql(variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data or not data.get("data", {}).get("user"):
        raise SystemExit(f"GitHub API error: {data.get('errors', data)}")
    return data["data"]["user"]


def fetch_days():
    today = dt.datetime.now(dt.timezone.utc).date()
    created = gql({"login": USER, "from": f"{today.year}-01-01T00:00:00Z",
                   "to": f"{today.year}-01-02T00:00:00Z"})["createdAt"]
    start_year = int(created[:4])
    days = {}
    for year in range(start_year, today.year + 1):
        frm = dt.date(year, 1, 1)
        to = min(dt.date(year, 12, 31), today)
        u = gql({"login": USER, "from": f"{frm}T00:00:00Z", "to": f"{to}T23:59:59Z"})
        for w in u["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
    return days


def compute(days, today):
    dates = sorted(days)
    total = sum(days.values())
    longest = run = 0
    prev = None
    longest_range = None
    run_start = None
    for d in dates:
        day = dt.date.fromisoformat(d)
        if days[d] > 0:
            if prev is not None and (day - prev).days == 1 and run > 0:
                run += 1
            else:
                run, run_start = 1, day
            if run > longest:
                longest, longest_range = run, (run_start, day)
            prev = day
        else:
            run, prev = 0, None
    # current streak: counts back from today, or from yesterday if today is still empty
    cur = 0
    day = today
    if days.get(day.isoformat(), 0) == 0:
        day -= dt.timedelta(days=1)
    while days.get(day.isoformat(), 0) > 0:
        cur += 1
        day -= dt.timedelta(days=1)
    return total, cur, longest


def svg(total, cur, longest):
    def col(x, big, label, accent=False):
        fill = "#ff8fa3" if accent else "#ffffff"
        return (f'<text x="{x}" y="88" text-anchor="middle" font-size="44" font-weight="700" fill="{fill}">{big}</text>'
                f'<text x="{x}" y="122" text-anchor="middle" font-size="16" fill="#f3d9de">{label}</text>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="700" height="170" viewBox="0 0 700 170" role="img" aria-label="Contribution streak">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#800020"/><stop offset="1" stop-color="#14070b"/></linearGradient></defs>
  <rect width="700" height="170" rx="16" fill="url(#g)"/>
  <g font-family="'Segoe UI', Arial, sans-serif">
    {col(117, total, "Total contributions")}
    {col(350, cur, "Current streak (days)", True)}
    {col(583, longest, "Longest streak (days)")}
    <line x1="233" y1="45" x2="233" y2="130" stroke="#ffffff" opacity="0.2"/>
    <line x1="467" y1="45" x2="467" y2="130" stroke="#ffffff" opacity="0.2"/>
    <text x="350" y="155" text-anchor="middle" font-size="12" fill="#ffffff" opacity="0.55">Updated {dt.datetime.now(dt.timezone.utc):%Y-%m-%d} UTC</text>
  </g>
</svg>
'''


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    if "--mock" in sys.argv:
        days = {}
        for i in range(400):
            d = today - dt.timedelta(days=i)
            days[d.isoformat()] = 0 if (i in (0, 40, 41, 150) or 200 < i < 215) else 2
    else:
        if not TOKEN:
            raise SystemExit("GH_TOKEN is not set")
        days = fetch_days()
    total, cur, longest = compute(days, today)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg(total, cur, longest))
    print(f"total={total} current={cur} longest={longest} -> {OUT}")


if __name__ == "__main__":
    main()
