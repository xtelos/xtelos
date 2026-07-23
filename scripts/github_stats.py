"""Live GitHub numbers for the profile's activity block.

Pulls the public contribution calendar (GraphQL) and the latest public push
(REST). Auth comes from GITHUB_TOKEN, falling back to the gh CLI for local
runs. Raises rather than returning bad data, so the generator fails loudly
instead of overwriting a good panel with zeros.
"""

import json
import os
import pathlib
import subprocess
import urllib.request

LOGIN = "xtelos"
BASELINE = "▁"      # a day with nothing on it
BARS = "▂▃▄▅▆▇█"    # any day with something, so activity always clears the floor

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
    try:
        run = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if run.returncode == 0 and run.stdout.strip():
            return run.stdout.strip()
    except FileNotFoundError:
        pass
    hosts = pathlib.Path.home() / ".config" / "gh" / "hosts.yml"
    if hosts.exists():
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
    # Default-branch pushes only, so this row cannot contradict the
    # contribution counts (branch pushes are not calendar contributions).
    events = gh_request(
        f"https://api.github.com/users/{LOGIN}/events/public?per_page=100"
    )
    for ev in events:
        if ev["type"] == "PushEvent" and ev["payload"].get("ref") in (
            "refs/heads/main",
            "refs/heads/master",
        ):
            return ev["repo"]["name"], ev["created_at"][:10]
    return None


def sparkline(counts):
    """One block per day.

    A zero day draws BASELINE rather than a dot: a dot reads as part of the
    row's dotted leader instead of as a chart. Nonzero days start one step
    above the floor, so the two are never the same glyph and the renderer can
    colour them apart by character.
    """
    peak = max(counts) or 1
    return "".join(
        BASELINE if n == 0 else BARS[min(len(BARS) - 1, (n * len(BARS)) // (peak + 1))]
        for n in counts
    )


def collect():
    """Everything the activity block needs, as a plain dict."""
    counts = [d["contributionCount"] for d in contribution_days()]
    return {
        "d7": sum(counts[-7:]),
        "d30": sum(counts[-30:]),
        "spark": sparkline(counts[-30:]),
        "push": latest_public_push(),
    }
