"""Generate the animated hero terminal (assets/hero-dark.svg, assets/hero-light.svg).

Run manually after editing; the output is committed. The typing effect is
per-character opacity with staggered delays: the one animation primitive that
renders identically everywhere GitHub's camo proxy serves the image.
"""

import pathlib

from terminal_svg import THEMES, esc, window

WIDTH = 830
HEIGHT = 252
BODY_X = 22
FIRST_LINE_Y = 74
LINE_H = 27

TYPE_SPEED = 0.06  # seconds per character
OUT_DELAY = 0.30   # pause between a command finishing and its output
GAP = 0.55         # pause before the next prompt


def show(delay):
    return f'style="animation-delay:{delay:.2f}s"'


class Timeline:
    def __init__(self):
        self.t = 0.2
        self.rows = []
        self.line = 0

    def y(self):
        return FIRST_LINE_Y + self.line * LINE_H

    def command(self, cmd, colors):
        """A prompt line whose command types out character by character."""
        y = self.y()
        spans = [
            f'<tspan class="c" fill="{colors["prompt"]}" {show(self.t)}>➜ </tspan>',
            f'<tspan class="c" fill="{colors["tilde"]}" {show(self.t)}>~ </tspan>',
        ]
        self.t += 0.30
        for ch in cmd:
            spans.append(f'<tspan class="c" {show(self.t)}>{esc(ch)}</tspan>')
            self.t += TYPE_SPEED
        self.rows.append(
            f'<text x="{BODY_X}" y="{y}" xml:space="preserve" fill="{colors["text"]}">{"".join(spans)}</text>'
        )
        self.line += 1
        self.t += OUT_DELAY

    def output(self, spans_fn, colors):
        """An output line that appears at once, after its command."""
        y = self.y()
        self.rows.append(
            f'<text class="c" x="{BODY_X}" y="{y}" xml:space="preserve" {show(self.t)}>{spans_fn(colors)}</text>'
        )
        self.line += 1
        self.t += GAP


def out_whoami(c):
    return (
        f'<tspan fill="{c["text"]}">Dylan Fodor</tspan>'
        f'<tspan fill="{c["dim"]}"> · </tspan>'
        f'<tspan fill="{c["text"]}">Full-Stack Developer</tspan>'
    )


def out_tools(c):
    names = ["argus", "aegis", "iris", "demeter", "ariadne", "delphi"]
    return "".join(f'<tspan fill="{c["accent"]}">{n}/</tspan><tspan> </tspan>' for n in names)


def out_focus(c):
    return f'<tspan fill="{c["warm"]}">Building fast, reliable systems</tspan>'


def build(theme_name):
    colors = THEMES[theme_name]
    tl = Timeline()
    tl.command("whoami", colors)
    tl.output(out_whoami, colors)
    tl.command("ls ~/tools", colors)
    tl.output(out_tools, colors)
    tl.command("cat focus.txt", colors)
    tl.output(out_focus, colors)

    cursor_t = tl.t - GAP + 0.15
    cursor_y = FIRST_LINE_Y + (tl.line - 1) * LINE_H
    # 31 chars of "Building fast, reliable systems" at ~9px/char in a 15px mono
    cursor = (
        f'<rect class="cursor" x="{BODY_X + 31 * 9.05 + 6}" y="{cursor_y - 13}" '
        f'width="9" height="17" fill="{colors["text"]}" '
        f'style="animation-delay:{cursor_t:.2f}s"/>'
    )

    style = """
.c { opacity: 0; animation: appear 0.01s steps(1, end) forwards; }
@keyframes appear { to { opacity: 1; } }
.cursor { opacity: 0; animation: blink 1.1s steps(1, end) infinite; }
@keyframes blink { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) {
  .c { animation-delay: 0s !important; }
  .cursor { animation: none; opacity: 1; }
}
"""
    return window(
        theme_name, WIDTH, HEIGHT, "dylan@xtelos - zsh",
        "\n".join(tl.rows) + "\n" + cursor, style,
    )


def main():
    assets = pathlib.Path(__file__).resolve().parent.parent / "assets"
    assets.mkdir(exist_ok=True)
    for theme in ("dark", "light"):
        path = assets / f"hero-{theme}.svg"
        path.write_text(build(theme))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
