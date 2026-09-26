"""Generate the whole profile as one terminal session.

Writes two files, a desktop panel and a phone one. The README is a single
<picture> that picks the right one, so the profile page is the terminal rather
than a banner sitting on top of markdown. There is no light variant; see
terminal_svg for why the theme switch had to go.

Copy is written to land on one line per entry at the desktop layout's 84
columns of value width (96 columns less the 12-column label gutter). A
description that runs over wraps to a second line and costs height in a panel
whose height is what a reader has to scroll past, so `python3 -c` the lengths
before adding a clause.

Nothing here depends on animation to become visible, and that is deliberate.
An earlier version typed the session out with staggered per-character opacity
delays. It rendered correctly in a page, and unreliably once GitHub served it
through <img>: characters and whole lines stayed hidden permanently, in an
order the delays cannot produce (a prompt at 0.087s missing while its own
command text at 0.148s showed). A browser that never runs the animation, or
runs part of it, must still show the whole profile, so the only animation left
is the cursor blink, and the cursor is visible with it disabled.

Everything drawn is static copy, so output only changes when this file does.
Run it after editing copy and commit README.md with the assets. The nightly
workflow reruns it too, which is a no-op unless someone committed copy without
regenerating; then it commits the regenerated panel. Output is committed.
"""

import hashlib
import pathlib
import re
import sys
import textwrap

from terminal_svg import COLORS, LAYOUTS, esc, window

SEP = " · "

# Each value is a list of items so a row that has to wrap (the phone layout)
# breaks between items, never inside one: "REST and JSON-RPC" / "APIs" reads
# as two things. Keep every item under the narrow layout's 41 usable columns.
STACK = [
    ("languages", ["Python", "JavaScript", "TypeScript", "PHP", "SQL"]),
    ("ai", ["LLM integration (Gemini, OpenAI)", "evals",
            "MCP tools for coding agents"]),
    ("backend", ["FastAPI", "Node.js", "REST and JSON-RPC APIs"]),
    ("frontend", ["JavaScript single-page apps", "React", "Next.js"]),
    ("data", ["PostgreSQL", "MySQL"]),
    ("infra", ["GitHub Actions CI", "Docker", "Linux"]),
]


def span(text, fill=None):
    f = f' fill="{fill}"' if fill else ""
    return f"<tspan{f}>{esc(text)}</tspan>"


def wrap_items(items, width):
    """Join items with SEP, breaking lines only between items.

    A wrapped line ends with a trailing middot so the reader can see the row
    continues. An item longer than `width` on its own falls back to textwrap
    rather than overrunning the window.
    """
    lines, line = [], ""
    for item in items:
        candidate = f"{line}{SEP}{item}" if line else item
        # Reserve room for the trailing " ·" a continued line carries.
        if line and len(candidate) + len(SEP.rstrip()) > width:
            lines.append(line + SEP.rstrip())
            line = item
        else:
            line = candidate
        if len(line) > width:
            *head, line = textwrap.wrap(line, width)
            lines.extend(head)
    lines.append(line)
    return lines


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
        """label + item-list rows; the narrow layout stacks them instead.

        `spaced` only affects the stacked form, where entries that wrap need a
        blank between them to stay legible and one-liners do not.
        """
        L = self.L
        if L.inline_labels:
            for label, items in pairs:
                wrapped = wrap_items(items, L.cols - L.label_w)
                self.out(span(label.ljust(L.label_w), label_fill)
                         + span(wrapped[0], value_fill))
                for cont in wrapped[1:]:
                    self.out(span(" " * L.label_w + cont, value_fill))
        else:
            for i, (label, items) in enumerate(pairs):
                if i and spaced:
                    self.blank()
                self.out(span(label, label_fill))
                for cont in wrap_items(items, L.cols - 2):
                    self.out(span("  " + cont, value_fill))

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


def build(layout):
    c = COLORS
    s = Session(layout, c)

    s.command("whoami")
    s.packed(
        [("Dylan Fodor", c["text"]),
         ("Apps Dev", c["text"]),
         ("Software Consulting Services", c["dim"])],
        " · ",
    )
    s.end_block()

    s.command("cat stack.txt")
    s.labeled(STACK, c["accent"], c["text"], spaced=False)
    s.end_block()

    s.cursor()
    return window(layout, s.height, layout.title, "\n".join(s.rows), STYLE)


def stamp_readme(readme, digests):
    """Point the README <picture> at ?v=<content hash> for each asset.

    The asset paths never change, so a client that cached one holds it under a
    URL the next version reuses. That is not hypothetical: a merge that removed
    two whole sections went live on main and the profile page kept serving the
    previous commit's SVG, byte for byte, through a hard refresh, while the same
    URL fetched directly returned the new one. Keying the URL to the content
    means a changed panel is a different URL and a stale copy can never be
    served for it, while an unchanged panel keeps its hash and stays cacheable.

    Only the two URLs are rewritten. The alt text is left alone: it has to stay
    on one line, because a blank line inside that raw HTML block ends the block
    and drops the <img> entirely.
    """
    text = original = readme.read_text()
    for name, digest in digests.items():
        # `profile\.svg` cannot match `profile-narrow.svg`; the escaped dot
        # pins the boundary, so the two substitutions stay independent.
        pattern = re.escape(name) + r"(?:\?v=[0-9a-f]+)?"
        text = re.sub(pattern, f"{name}?v={digest}", text)
    if text == original:
        print("unchanged README.md")
        return
    readme.write_text(text)
    print("stamped README.md")


def main():
    # No "updated <date>" in the titlebar on purpose. The generator only
    # rewrites a file whose content changed, and nothing drawn is dynamic, so
    # a generation stamp would freeze on the day the copy last changed and
    # then read as stale.
    root = pathlib.Path(__file__).resolve().parent.parent
    assets = root / "assets"
    assets.mkdir(exist_ok=True)
    digests = {}
    for layout in LAYOUTS:
        path = assets / layout.file
        svg = build(layout)
        # Hash what the file will hold, not what changed, so an unchanged asset
        # keeps the hash the README already carries.
        digests[f"assets/{layout.file}"] = hashlib.sha256(
            svg.encode()).hexdigest()[:8]
        if path.exists() and path.read_text() == svg:
            print(f"unchanged {path.name}")
            continue
        path.write_text(svg)
        print(f"wrote {path.name} ({len(svg)} bytes)")
    stamp_readme(root / "README.md", digests)


if __name__ == "__main__":
    sys.exit(main())
