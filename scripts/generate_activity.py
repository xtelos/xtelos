"""Generate the live activity panel (assets/activity-dark.svg, assets/activity-light.svg).

Run nightly by .github/workflows/refresh-activity.yml. Pulls the public
contribution calendar (GitHub GraphQL) and the latest public push (REST).
Pure stdlib; auth comes from the GITHUB_TOKEN env var. Fails loudly rather
than overwrite the committed panels with bad data.
"""

import datetime
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

from terminal_svg import THEMES, esc, window

LOGIN = "xtelos"
WIDTH = 830
HEIGHT = 204
BODY_X = 22
FIRST_LINE_Y = 80
LINE_H = 27

BLOCKS = "▁▂▃▄▅▆▇█"

CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def token():
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    # Local runs: borrow the gh CLI's token.
    run = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    if run.returncode == 0 and run.stdout.strip():
        return run.stdout.strip()
    hosts = pathlib.Path.home() / ".config" / "gh" / "hosts.yml"
    for line in hosts.read_text().splitlines():
        if "oauth_token:" in line:
            return line.split("oauth_token:", 1)[1].strip()
    raise RuntimeError("No GITHUB_TOKEN and no gh CLI token found")


def gh_request(url, payload=None):
    headers = {
        "Authorization": f"Bearer {token()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": LOGIN,
    }
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def contribution_days():
    body = gh_request(
        "https://api.github.com/graphql",
        {"query": CALENDAR_QUERY, "variables": {"login": LOGIN}},
    )
    if body.get("errors"):
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    days.sort(key=lambda d: d["date"])
    return days


def latest_public_push():
    events = gh_request(f"https://api.github.com/users/{LOGIN}/events/public")
    for ev in events:
        if ev["type"] == "PushEvent":
            return ev["repo"]["name"], ev["created_at"][:10]
    return None


def sparkline(counts):
    peak = max(counts) or 1
    out = []
    for n in counts:
        if n == 0:
            out.append("·")
        else:
            out.append(BLOCKS[min(len(BLOCKS) - 1, (n * len(BLOCKS)) // (peak + 1))])
    return "".join(out)


def build(theme_name, stats, refreshed):
    c = THEMES[theme_name]

    def row(i, label, value_spans):
        y = FIRST_LINE_Y + i * LINE_H
        pad = "·" * (22 - len(label))
        return (
            f'<text x="{BODY_X}" y="{y}" xml:space="preserve">'
            f'<tspan fill="{c["text"]}">{esc(label)} </tspan>'
            f'<tspan fill="{c["window_edge"]}">{pad}</tspan>'
            f'<tspan> </tspan>{value_spans}</text>'
        )

    d7, d30, spark, push = stats
    push_spans = (
        f'<tspan fill="{c["dim"]}">{esc(push[1])}  </tspan><tspan fill="{c["accent"]}">{esc(push[0])}</tspan>'
        if push
        else f'<tspan fill="{c["dim"]}">none lately (the private repos are where the action is)</tspan>'
    )
    rows = [
        f'<text x="{BODY_X}" y="{FIRST_LINE_Y - LINE_H}" xml:space="preserve">'
        f'<tspan fill="{c["prompt"]}">➜ </tspan><tspan fill="{c["tilde"]}">~ </tspan>'
        f'<tspan fill="{c["text"]}">tail activity.log</tspan></text>',
        row(0, "last 7 days", f'<tspan fill="{c["text"]}">{d7} contributions</tspan>'),
        row(1, "last 30 days", f'<tspan fill="{c["text"]}">{d30} contributions</tspan>'),
        row(2, "30-day trend", f'<tspan fill="{c["green"]}">{esc(spark)}</tspan>'),
        row(3, "latest public push", push_spans),
    ]
    title = f"dylan@xtelos - zsh · activity · refreshed {refreshed}"
    return window(theme_name, WIDTH, HEIGHT, title, "\n".join(rows))


def main():
    days = contribution_days()
    counts = [d["contributionCount"] for d in days]
    stats = (
        sum(counts[-7:]),
        sum(counts[-30:]),
        sparkline(counts[-30:]),
        latest_public_push(),
    )
    refreshed = datetime.date.today().isoformat()
    assets = pathlib.Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    for theme in ("dark", "light"):
        path = assets / f"activity-{theme}.svg"
        path.write_text(build(theme, stats, refreshed))
        print(f"wrote {path}")


if __name__ == "__main__":
    sys.exit(main())
