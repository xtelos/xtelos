"""Generate the whole profile as one terminal session.

Writes four files: {dark,light} x {desktop,narrow}. The README is a single
<picture> that picks the right one, so the profile page is the terminal rather
than a banner sitting on top of markdown.

Nothing here depends on animation to become visible, and that is deliberate.
An earlier version typed the session out with staggered per-character opacity
delays. It rendered correctly in a page, and unreliably once GitHub served it
through <img>: characters and whole lines stayed hidden permanently, in an
order the delays cannot produce (a prompt at 0.087s missing while its own
command text at 0.148s showed). A browser that never runs the animation, or
runs part of it, must still show the whole profile, so the only animation left
is the cursor blink, and the cursor is visible with it disabled.

Run manually after editing copy; the nightly workflow reruns it for the
activity numbers. Output is committed.
"""

import pathlib
import sys
import textwrap

import github_stats
from terminal_svg import LAYOUTS, THEMES, esc, window

LEADER = 21        # column where dotted-leader values start

TOOLS = [
    ("argus", "call/impact graph for a million-line legacy codebase, with cited "
              "file:line receipts instead of a grep sweep"),
    ("aegis", "build-trust engine that compiles on the real host; unparsed and "
              "unverified are never a pass, so it cannot report a false green"),
    ("iris", "headless visual verification over the Chrome DevTools Protocol: "
             "screenshots with a verdict, console errors caught at the protocol level"),
    ("demeter", "dev-database harness that stands up, seeds, and tears down per "
                "stack, and never wipes the thing you cannot rebuild"),
    ("ariadne", "long-effort tracker reporting the drift between what the tracker "
                "claims and what git says actually happened"),
    ("delphi", "personal knowledge engine: a linked note graph with scored recall, "
               "so hard-won context survives from one session to the next"),
    ("momus", "adversarial reviewer that assumes my change is broken and tries to "
              "prove it before anything gets called done"),
]

SHIPPED = [
    ("[auth]", "Multi-method 2FA end to end: authenticator-app TOTP, SMS, email, "
               "and 30-day trusted devices. Live across 90+ newspaper sites."),
    ("[payments]", "Provider-agnostic payment layer (Stripe, Square). Led a processor "
                   "migration with per-customer routing and a safe, re-runnable job "
                   "moving stored cards into a token vault."),
    ("[genai]", "Print-ready ad artwork from a text prompt: three interchangeable "
                "image models behind one interface, OCR text handling, and an "
                "automated check that rejects unusable output before it ships."),
    ("[adtech]", "Google Ad Manager integration: line items, advertisers, and "
                 "creatives created straight from order entry."),
    ("[solo]", "Multi-tenant classified-ads marketplace, sole developer: ad builder, "
               "checkout funnel, payments, approvals, email."),
]

STACK = [
    ("languages", "JavaScript · TypeScript · Python · PHP · SQL"),
    ("frontend", "React · Next.js · single-page apps that stay fast"),
    ("backend", "Node.js · Flask · Express · REST and JSON-RPC APIs"),
    ("data", "PostgreSQL · MySQL · MongoDB · Redis"),
    ("infra", "AWS · Docker · CI/CD · Linux"),
    ("ai", "LLM integration · image generation · speech to text"),
]

ABOUT = (
    "I build and modernize the software newspapers use to sell and produce "
    "advertising. I lean front-end but work the whole stack, and the work I'm "
    "proudest of is the load-bearing kind: two-factor auth, payment processing, "
    "and a generative-AI tool that makes print-ready ad artwork. Reliability "
    "first, because that's the part people only notice when it's missing."
)

JOKE = (
    "Commitment issues? Not me. I commit early, commit often, and only "
    "occasionally force-push something I'll regret."
)

TOOLS_INTRO = (
    "I run AI coding agents against real production code, and I got tired of "
    "\"trust me, it works.\" Each of these turns a category of guesswork into a "
    "measured verdict."
)

TOOLS_OUTRO = "Source private while they grow up; ask me about any of them."


def span(text, fill=None):
    f = f' fill="{fill}"' if fill else ""
    return f"<tspan{f}>{esc(text)}</tspan>"


def spark_spans(spark, colors):
    """Colour the sparkline's empty days apart from its active ones, in runs."""
    out, run, empty = [], "", spark[:1] == github_stats.BASELINE
    for ch in spark:
        is_empty = ch == github_stats.BASELINE
        if is_empty != empty:
            out.append(span(run, colors["rule"] if empty else colors["green"]))
            run, empty = "", is_empty
        run += ch
    out.append(span(run, colors["rule"] if empty else colors["green"]))
    return "".join(out)


class Session:
    """Lays terminal lines down the window."""

    def __init__(self, layout, colors):
        self.L = layout
        self.c = colors
        self.rows = []
        self.n = 0

    @property
    def y(self):
        return self.L.first_y + self.n * self.L.line_h

    def blank(self):
        self.n += 1

    def out(self, spans):
        """One output line.

        The line carries a fill of its own: an unfilled tspan (a separator, a
        space) would otherwise inherit SVG's default black and disappear
        against the dark theme.
        """
        self.rows.append(
            f'<text x="{self.L.pad_x}" y="{self.y}" xml:space="preserve" '
            f'fill="{self.c["dim"]}">{spans}</text>'
        )
        self.n += 1

    def command(self, cmd):
        c = self.c
        self.rows.append(
            f'<text x="{self.L.pad_x}" y="{self.y}" xml:space="preserve" '
            f'fill="{c["text"]}">'
            f'<tspan fill="{c["prompt"]}">➜ </tspan>'
            f'<tspan fill="{c["tilde"]}">~ </tspan>'
            f"<tspan>{esc(cmd)}</tspan></text>"
        )
        self.n += 1

    def end_block(self):
        self.blank()

    def prose(self, text, fill):
        for line in textwrap.wrap(text, self.L.cols):
            self.out(span(line, fill))

    def packed(self, items, sep):
        """Colored items flowed across as many lines as the width needs."""
        line, width = [], 0
        for text, fill in items:
            add = len(text) + (len(sep) if line else 0)
            if line and width + add > self.L.cols:
                self.out("".join(line))
                line, width = [], 0
                add = len(text)
            if line:
                line.append(span(sep))
                width += len(sep)
            line.append(span(text, fill))
            width += len(text)
        if line:
            self.out("".join(line))

    def labeled(self, pairs, label_fill, value_fill, spaced=True):
        """label + description rows; the narrow layout stacks them instead.

        `spaced` only affects the stacked form, where entries that wrap need a
        blank between them to stay legible and one-liners do not.
        """
        L = self.L
        if L.inline_labels:
            for label, value in pairs:
                wrapped = textwrap.wrap(value, L.cols - L.label_w) or [""]
                self.out(span(label.ljust(L.label_w), label_fill)
                         + span(wrapped[0], value_fill))
                for cont in wrapped[1:]:
                    self.out(span(" " * L.label_w + cont, value_fill))
        else:
            for i, (label, value) in enumerate(pairs):
                if i and spaced:
                    self.blank()
                self.out(span(label, label_fill))
                for cont in textwrap.wrap(value, L.cols - 2):
                    self.out(span("  " + cont, value_fill))

    def dotted(self, pairs, label_fill):
        """Dotted-leader rows; the narrow layout drops the value below."""
        L = self.L
        for label, value_spans in pairs:
            if L.inline_labels:
                leader = "·" * max(1, LEADER - len(label))
                self.out(span(f"{label} ", label_fill)
                         + span(leader, self.c["rule"])
                         + span(" ") + value_spans)
            else:
                self.out(span(label, label_fill))
                self.out(span("  ") + value_spans)

    def cursor(self):
        c = self.c
        self.rows.append(
            f'<text x="{self.L.pad_x}" y="{self.y}" xml:space="preserve">'
            f'<tspan fill="{c["prompt"]}">➜ </tspan>'
            f'<tspan fill="{c["tilde"]}">~ </tspan>'
            f'<tspan class="cursor" fill="{c["text"]}">▋</tspan>'
            f"</text>"
        )
        self.n += 1

    @property
    def height(self):
        return self.L.first_y + (self.n - 1) * self.L.line_h + self.L.bottom_pad


# The cursor is visible by default and the animation only blinks it off, so a
# renderer that drops the animation leaves a solid cursor rather than none.
STYLE = """
.cursor { animation: blink 1.1s steps(1, end) infinite; }
@keyframes blink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .cursor { animation: none; } }
"""


def build(layout, theme_name, stats):
    c = THEMES[theme_name]
    s = Session(layout, c)

    s.command("whoami")
    s.packed(
        [("Dylan Fodor", c["text"]),
         ("Full-Stack Developer", c["text"]),
         ("Software Consulting Services", c["dim"])],
        " · ",
    )
    s.end_block()

    s.command("cat about.txt")
    s.prose(ABOUT, c["text"])
    s.blank()
    s.prose(JOKE, c["dim"])
    s.end_block()

    s.command("ls ~/tools")
    s.packed([(f"{name}/", c["accent"]) for name, _ in TOOLS], "  ")
    s.end_block()

    s.command("cat ~/tools/README")
    s.prose(TOOLS_INTRO, c["dim"])
    s.blank()
    s.labeled(TOOLS, c["accent"], c["text"])
    s.blank()
    s.prose(TOOLS_OUTRO, c["dim"])
    s.end_block()

    s.command("tail shipped.log")
    s.labeled(SHIPPED, c["warm"], c["text"])
    s.end_block()

    s.command("tail activity.log")
    # Values in this block are not wrapped, so they have to be sized to the
    # layout: a repo name long enough to overrun the phone window would print
    # straight out through the side of it.
    budget = (layout.cols - LEADER - 2) if layout.inline_labels else (layout.cols - 2)
    push = stats["push"]
    if push:
        repo, when = push[0], push[1]
        room = budget - len(when) - 2
        if len(repo) > room:
            repo = repo[: max(1, room - 1)] + "…"
        push_spans = span(when, c["dim"]) + span("  ") + span(repo, c["accent"])
    else:
        push_spans = span("none lately; private repos, mostly"[:budget], c["dim"])
    unit = "pull request" + ("" if stats["merged_short"] == 1 else "s")
    repos = f"{stats['repos']} repositor" + ("y" if stats["repos"] == 1 else "ies")
    s.dotted(
        [
            ("merged, last 7d", span(f"{stats['merged_short']} {unit}", c["text"])),
            ("merged, last 30d",
             span(f"{stats['merged_long']} across {repos}", c["text"])),
            ("30-day trend", spark_spans(stats["spark"], c)),
            ("active days", span(f"{stats['active_days']} of the last 30", c["text"])),
            ("latest public push", push_spans),
        ],
        c["text"],
    )
    s.end_block()

    s.command("cat stack.txt")
    s.labeled(STACK, c["accent"], c["text"], spaced=False)
    s.end_block()

    s.cursor()
    return window(layout, theme_name, s.height, layout.title,
                  "\n".join(s.rows), STYLE)


def main():
    # No "updated <date>" in the titlebar on purpose. The generator only
    # rewrites a file whose content changed, so a generation stamp would
    # freeze on the last day the numbers moved and then read as stale. The
    # `latest public push` row is the freshness signal, and it is a real one.
    stats = github_stats.collect()
    assets = pathlib.Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    for layout in LAYOUTS:
        for theme in ("dark", "light"):
            path = assets / f"profile-{layout.name}{theme}.svg"
            svg = build(layout, theme, stats)
            if path.exists() and path.read_text() == svg:
                print(f"unchanged {path.name}")
                continue
            path.write_text(svg)
            print(f"wrote {path.name} ({len(svg)} bytes)")


if __name__ == "__main__":
    sys.exit(main())
