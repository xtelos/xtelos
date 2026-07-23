"""Shared terminal-window chrome for the profile's SVG panels.

Both generators (hero, activity) render into the same macOS-style terminal
window so every panel on the profile reads as one system. Pure stdlib.
"""

from html import escape

FONT = "ui-monospace, 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', monospace"

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
    },
}

TITLEBAR_H = 36
DOT_COLORS = ("#ff5f57", "#febc2e", "#28c840")


def esc(s):
    return escape(s, quote=True)


def window(theme_name, width, height, title, body, extra_style=""):
    """Wrap `body` (svg fragment) in the terminal window chrome."""
    t = THEMES[theme_name]
    dots = "".join(
        f'<circle cx="{22 + i * 20}" cy="{TITLEBAR_H / 2}" r="6" fill="{c}"/>'
        for i, c in enumerate(DOT_COLORS)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">
<style>
text {{ font-family: {FONT}; font-size: 15px; }}
.title {{ font-size: 13px; fill: {t["title_text"]}; }}
{extra_style}
</style>
<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{t["glow_top"]}"/>
<stop offset="1" stop-color="{t["window"]}"/>
</linearGradient>
<clipPath id="win"><rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="11"/></clipPath>
</defs>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="11.5" fill="url(#bg)" stroke="{t["window_edge"]}"/>
<g clip-path="url(#win)">
<rect x="1" y="1" width="{width - 2}" height="{TITLEBAR_H - 1}" fill="{t["titlebar"]}"/>
<line x1="1" y1="{TITLEBAR_H}" x2="{width - 1}" y2="{TITLEBAR_H}" stroke="{t["window_edge"]}" stroke-width="1"/>
</g>
{dots}
<text class="title" x="{width / 2}" y="{TITLEBAR_H / 2 + 4.5}" text-anchor="middle">{esc(title)}</text>
{body}
</svg>
'''
