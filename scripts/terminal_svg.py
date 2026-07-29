"""Shared terminal-window chrome for the profile SVG.

The whole profile is one terminal session, rendered at two widths: a desktop
layout and a phone layout that `<picture>` swaps in under 720px. Everything a
layout needs to reflow (column budget, metrics, chrome scale) lives in Layout,
so the content is written once and drawn twice. Pure stdlib.

One palette, not two. There used to be a light variant selected with
`prefers-color-scheme`, and it broke the width switch: GitHub wraps any
`<picture>` carrying a color-scheme query in its own `themed-picture` element,
which resolves the theme half of a combined query and ignores the width half,
so a dark-theme reader got the 460px phone panel on a 1400px desktop. The two
conditions cannot be combined reliably, and width is the one that decides
whether the thing is legible at all. A terminal is dark anyway, and a dark
panel reads as deliberate on a light page.
"""

from dataclasses import dataclass
from html import escape

FONT = "ui-monospace, 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

# Widest advance among the fonts in the stack (DejaVu/Menlo sit at ~0.602em;
# Consolas is narrower). Column budgets are sized against the worst case so a
# line never overruns the window on somebody else's machine.
ADVANCE = 0.602

COLORS = {
    "window": "#15161e",
    "window_edge": "#2a2b3a",
    "glow_top": "#1b1d29",
    "titlebar": "#1b1c26",
    "title_text": "#6b6d80",
    "text": "#e6edf3",
    "dim": "#8b8fa3",
    "prompt": "#7ee787",
    "tilde": "#79c0ff",
    "accent": "#79c0ff",
    "warm": "#ffa657",
    "green": "#39d353",
    "rule": "#2a2b3a",
}

DOT_COLORS = ("#ff5f57", "#febc2e", "#28c840")


@dataclass(frozen=True)
class Layout:
    file: str          # asset filename, referenced by the README <picture>
    width: int
    font: int
    line_h: int
    pad_x: int
    titlebar: int
    dot_r: float
    dot_x: float
    dot_gap: float
    title: str
    cols: int          # usable character columns for body text
    label_w: int       # column width of the label gutter (rows/log blocks)
    inline_labels: bool  # False: label gets its own line, value indents below

    @property
    def first_y(self):
        return self.titlebar + self.font + 16

    @property
    def bottom_pad(self):
        return self.line_h


# Column budgets are deliberately a few short of what fits, so a font with a
# wider advance than DejaVu still lands inside the window.
# 960 is the width of GitHub's README column, near enough: the profile box runs
# ~900-980px depending on the viewport, so the panel renders about 1:1 and the
# 15px body text stays 15px. It was 1200 before, which bought longer lines but
# had GitHub scale the whole thing to ~0.75 and the text down to ~11px. Longer
# lines are still the only lever against scrolling (the panel has a fixed
# aspect ratio), so the copy is written tight rather than the panel drawn wide.
WIDE = Layout(
    file="profile.svg", width=960, font=15, line_h=27, pad_x=24, titlebar=36,
    dot_r=6, dot_x=24, dot_gap=20, title="dylan@xtelos: ~ · zsh",
    cols=96, label_w=12, inline_labels=True,
)

NARROW = Layout(
    file="profile-narrow.svg", width=460, font=15, line_h=24, pad_x=16,
    titlebar=30, dot_r=5, dot_x=17, dot_gap=16, title="dylan@xtelos · zsh",
    cols=45, label_w=0, inline_labels=False,
)

LAYOUTS = (WIDE, NARROW)


def esc(s):
    return escape(s, quote=True)


def window(layout, height, title, body, extra_style=""):
    """Wrap `body` (an svg fragment) in the terminal window chrome."""
    t = COLORS
    w = layout.width
    dots = "".join(
        f'<circle cx="{layout.dot_x + i * layout.dot_gap}" cy="{layout.titlebar / 2}" '
        f'r="{layout.dot_r}" fill="{c}"/>'
        for i, c in enumerate(DOT_COLORS)
    )
    title_size = round(layout.font * 0.87, 1)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {height}" width="{w}" height="{height}" role="img">
<style>
text {{ font-family: {FONT}; font-size: {layout.font}px; }}
.title {{ font-size: {title_size}px; fill: {t["title_text"]}; }}
{extra_style}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{t["glow_top"]}"/>
<stop offset="1" stop-color="{t["window"]}"/>
</linearGradient>
<clipPath id="win"><rect x="1" y="1" width="{w - 2}" height="{height - 2}" rx="11"/></clipPath>
</defs>
<rect x="0.5" y="0.5" width="{w - 1}" height="{height - 1}" rx="11.5" fill="url(#bg)" stroke="{t["window_edge"]}"/>
<g clip-path="url(#win)">
<rect x="1" y="1" width="{w - 2}" height="{layout.titlebar - 1}" fill="{t["titlebar"]}"/>
<line x1="1" y1="{layout.titlebar}" x2="{w - 1}" y2="{layout.titlebar}" stroke="{t["window_edge"]}" stroke-width="1"/>
</g>
{dots}
<text class="title" x="{w / 2}" y="{layout.titlebar / 2 + title_size * 0.35 + 0.5:.1f}" text-anchor="middle">{esc(title)}</text>
{body}
</svg>
'''
