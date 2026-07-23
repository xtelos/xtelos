"""Live numbers for the profile's activity block.

Deliberately NOT GitHub's contribution graph. That graph counts only commits
on a repo's default branch, and only in repos it is allowed to show, which
between them hid about 99% of real work here: 567 commits pushed in a week
scored as 2. This measures merged pull requests instead, which survives both
problems and, unlike a commit count, is not inflated by rebases and backup
branches carrying duplicate SHAs of the same work.

Auth comes from PROFILE_TOKEN (a PAT that can see private repos), falling
back to GITHUB_TOKEN and then the gh CLI for local runs. Every number is
guarded: a token that cannot see private repositories makes this raise rather
than quietly publish the public-only view, which for this account is 1 merged
PR instead of 182.
"""

import datetime
import json
import os
import pathlib
import subprocess
import urllib.error
import urllib.parse
import urllib.request

LOGIN = "xtelos"
BASELINE = "▁"      # a day with nothing on it
BARS = "▂▃▄▅▆▇█"    # any day with something, so activity always clears the floor

WINDOW_SHORT = 7
WINDOW_LONG = 30
SEARCH = "https://api.github.com/search/issues"


def token():
    for var in ("PROFILE_TOKEN", "GITHUB_TOKEN"):
        tok = os.environ.get(var)
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
    raise RuntimeError(
        "No PROFILE_TOKEN, no GITHUB_TOKEN and no gh CLI token found. "
        "The activity block needs a token that can read private repositories."
    )


def gh_request(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token()}",
        "Accept": "application/vnd.github+json",
        "User-Agent": LOGIN,
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GitHub returned {e.code} for {url}: {e.read()[:300]}") from e


def _search(query, page=1):
    q = urllib.parse.urlencode({"q": query, "per_page": 100, "page": page})
    return gh_request(f"{SEARCH}?{q}")


def search_count(query):
    """Result count only. total_count is exact and costs one request."""
    return _search(query)["total_count"]


def search_items(query, max_pages=10):
    items = []
    for page in range(1, max_pages + 1):
        body = _search(query, page)
        items += body["items"]
        if len(items) >= body["total_count"] or not body["items"]:
            break
    return items


def merged_query(since, extra=""):
    return f"is:pr author:{LOGIN} is:merged merged:>={since}{extra}"


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


def latest_public_push():
    """Most recent default-branch push to a PUBLIC repo.

    Public timeline only, on purpose: this is the one row that names a
    repository, and the rest of the account's work lives in private repos
    whose names do not belong on a public profile.
    """
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


def collect():
    """Everything the activity block needs, as a plain dict."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    since_short = today - datetime.timedelta(days=WINDOW_SHORT - 1)
    since_long = today - datetime.timedelta(days=WINDOW_LONG - 1)

    merged_short = search_count(merged_query(since_short))
    merged_long = search_count(merged_query(since_long))
    private_long = search_count(merged_query(since_long, " is:private"))

    # Never publish a number the token was not able to earn. A bot token sees
    # public repos only, which here means 1 merged PR rather than 182, and a
    # profile that silently claims the work stopped is worse than a failed job.
    if merged_long == 0:
        raise RuntimeError(
            f"No merged PRs found in the last {WINDOW_LONG} days. Refusing to "
            "publish; this is far more likely to be a bad token than a fact."
        )
    if private_long == 0:
        raise RuntimeError(
            "This token cannot see merged PRs in private repositories, so the "
            f"counts would be public-only ({merged_long} instead of the real "
            "total). Set PROFILE_TOKEN to a PAT with repo scope."
        )

    per_day = {str(today - datetime.timedelta(days=d)): 0 for d in range(WINDOW_LONG)}
    repos = set()
    for item in search_items(merged_query(since_long)):
        when = (item.get("pull_request") or {}).get("merged_at") or item["closed_at"]
        day = when[:10]
        if day in per_day:
            per_day[day] += 1
        repos.add(item["repository_url"].split("/repos/", 1)[1])

    counts = [per_day[str(today - datetime.timedelta(days=d))]
              for d in range(WINDOW_LONG - 1, -1, -1)]

    return {
        "merged_short": merged_short,
        "merged_long": merged_long,
        "repos": len(repos),
        "spark": sparkline(counts),
        "active_days": sum(1 for n in counts if n),
        "push": latest_public_push(),
    }
