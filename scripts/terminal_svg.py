"""Shared terminal-window chrome for the profile SVG.

The whole profile is one terminal session, rendered at two widths: a desktop
layout and a phone layout that `<picture>` swaps in under 500px. Everything a
layout needs to reflow (column budget, metrics, chrome scale) lives in Layout,
so the content is written once and drawn twice. Pure stdlib.
"""

from dataclasses import dataclass
from html import escape

FONT = "ui-monospace, 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

# Widest advance among the fonts in the stack (DejaVu/Menlo sit at ~0.602em;
# Consolas is narrower). Column budgets are sized against the worst case so a
# line never overruns the window on somebody else's machine.
ADVANCE = 0.602

THEMES = {
    "dark": {
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
    },
    "light": {
        "window": "#ffffff",
        "window_edge": "#d0d7de",
        "glow_top": "#fbfcfd",
        "titlebar": "#f6f8fa",
        "title_text": "#57606a",
        "text": "#1f2328",
        "dim": "#6e7781",
        "prompt": "#1a7f37",
        "tilde": "#0969da",
        "accent": "#0969da",
        "warm": "#953800",
        "green": "#1a7f37",
        "rule": "#d8dee4",
    },
}

DOT_COLORS = ("#ff5f57", "#febc2e", "#28c840")


@dataclass(frozen=True)
class Layout:
    name: str
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
# Drawn wide on purpose. The panel keeps a fixed aspect ratio, so the only way
# to cut how far a reader scrolls is to spend width on longer lines: 82 columns
# gave a 2.29 aspect, 120 gives 1.36, which is nearly half the scrolling at any
# render size. It also stops the terminal sitting in a puddle of whitespace in
# GitHub's README column.
WIDE = Layout(
    name="", width=1200, font=15, line_h=27, pad_x=24, titlebar=36,
    dot_r=6, dot_x=24, dot_gap=20, title="dylan@xtelos: ~ · zsh",
    cols=120, label_w=12, inline_labels=True,
)

NARROW = Layout(
    name="narrow-", width=460, font=15, line_h=24, pad_x=16, titlebar=30,
    dot_r=5, dot_x=17, dot_gap=16, title="dylan@xtelos · zsh",
    cols=45, label_w=0, inline_labels=False,
)

LAYOUTS = (WIDE, NARROW)


def esc(s):
    return escape(s, quote=True)


def window(layout, theme_name, height, title, body, extra_style=""):
    """Wrap `body` (an svg fragment) in the terminal window chrome."""
    t = THEMES[theme_name]
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
