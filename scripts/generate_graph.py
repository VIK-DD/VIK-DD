import json
import os
import datetime
import urllib.request

USERNAME = "VIK-DD"
TOKEN = os.environ["GH_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""

COLORS = {
    0: "#2d333b",
    1: "#28502c",
    2: "#3a7a34",
    3: "#529c3d",
    4: "#6cc644",
}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_days():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USERNAME}}).encode(),
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.load(resp)
    weeks = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append((datetime.date.fromisoformat(day["date"]), day["contributionCount"]))
    return days


def gh_weekday(d):
    # Sunday = 0 .. Saturday = 6 (matches GitHub's own layout)
    return (d.weekday() + 1) % 7


def level_for(count, max_count):
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio > 0.75:
        return 4
    if ratio > 0.5:
        return 3
    if ratio > 0.25:
        return 2
    return 1


def build_svg(days):
    min_date = min(d for d, _ in days)
    anchor_sunday = min_date - datetime.timedelta(days=gh_weekday(min_date))
    max_count = max((c for _, c in days), default=0)

    grid = {}
    max_week = 0
    for d, c in days:
        wd = gh_weekday(d)
        week = (d - anchor_sunday).days // 7
        grid[(week, wd)] = (d, c)
        max_week = max(max_week, week)
    total_weeks = max_week + 1

    cell, gap = 10, 3
    step = cell + gap
    margin_left, margin_top = 28, 20
    width = margin_left + total_weeks * step + 4
    height = margin_top + 7 * step + 4

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
    ]

    last_month = None
    for week in range(total_weeks):
        rep_date = None
        for wd in range(7):
            if (week, wd) in grid:
                rep_date = grid[(week, wd)][0]
                break
        if rep_date is None:
            continue
        if rep_date.month != last_month:
            x = margin_left + week * step
            parts.append(
                f'<text x="{x}" y="12" font-family="Helvetica,Arial,sans-serif" '
                f'font-size="10" fill="#8b949e">{MONTH_NAMES[rep_date.month - 1]}</text>'
            )
            last_month = rep_date.month

    for wd, label in {1: "Mon", 3: "Wed", 5: "Fri"}.items():
        y = margin_top + wd * step + cell - 1
        parts.append(
            f'<text x="0" y="{y}" font-family="Helvetica,Arial,sans-serif" '
            f'font-size="9" fill="#8b949e">{label}</text>'
        )

    for week in range(total_weeks):
        for wd in range(7):
            x = margin_left + week * step
            y = margin_top + wd * step
            if (week, wd) in grid:
                d, c = grid[(week, wd)]
                lvl = level_for(c, max_count)
                fill = COLORS[lvl]
                plural = "s" if c != 1 else ""
                title = f"{d.isoformat()}: {c} contribution{plural}"
            else:
                fill = COLORS[0]
                title = ""
            rect = (
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'rx="2" ry="2" fill="{fill}">'
            )
            if title:
                rect += f"<title>{title}</title>"
            rect += "</rect>"
            parts.append(rect)

    parts.append("</svg>")
    return "\n".join(parts)


def main():
    days = fetch_days()
    svg = build_svg(days)
    with open("activity-graph.svg", "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
