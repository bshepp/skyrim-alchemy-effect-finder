"""WCAG AA contrast checks over the stylesheet's color tokens (508 gate).

Parses the custom-property palettes for both themes straight out of
style.css and verifies every foreground/background pairing the UI actually
uses. Section 508 incorporates WCAG 2.x AA: 4.5:1 for normal text, 3:1 for
large text and meaningful UI components (focus outlines, active-tab
underlines).
"""
import re
from pathlib import Path

import pytest

CSS = (Path(__file__).parents[2]
       / "alchemy_helper" / "web" / "static" / "style.css")

# (foreground token, background token, minimum ratio)
TEXT = 4.5
LARGE_OR_UI = 3.0
PAIRS = [
    ("--text", "--bg", TEXT),
    ("--text", "--bg-alt", TEXT),
    ("--text", "--bg-raised", TEXT),
    ("--text-dim", "--bg", TEXT),
    ("--text-dim", "--bg-alt", TEXT),
    ("--text-dim", "--bg-raised", TEXT),
    ("--text-faint", "--bg-alt", TEXT),        # the ??? cells
    ("--accent", "--bg", TEXT),                # links on page background
    ("--accent", "--bg-alt", TEXT),            # links inside cards
    ("--accent", "--bg-raised", LARGE_OR_UI),  # hover borders, focus rings
    ("--danger", "--bg", TEXT),
    ("--amber-text", "--amber-bg", TEXT),
    ("--red-text", "--red-bg", TEXT),
    ("--badge-save-text", "--badge-save-bg", TEXT),
    ("--badge-manual-text", "--badge-manual-bg", TEXT),
    ("--known-text", "--known-bg", TEXT),
]


def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _palette(block: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})\s*;", block))


def _theme_blocks() -> dict[str, dict[str, str]]:
    css = CSS.read_text(encoding="utf-8")
    dark_m = re.search(r":root\s*\{(.*?)\}", css, re.S)
    light_m = re.search(r':root\[data-theme="light"\]\s*\{(.*?)\}', css, re.S)
    assert dark_m, "no :root token block in style.css"
    assert light_m, "no light-theme token block in style.css"
    dark = _palette(dark_m.group(1))
    # light theme inherits dark's tokens and overrides them
    light = {**dark, **_palette(light_m.group(1))}
    return {"dark": dark, "light": light}


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_all_declared_pairs_meet_wcag_aa(theme):
    palette = _theme_blocks()[theme]
    failures = []
    for fg, bg, minimum in PAIRS:
        assert fg in palette, f"{theme}: token {fg} missing from palette"
        assert bg in palette, f"{theme}: token {bg} missing from palette"
        ratio = contrast(palette[fg], palette[bg])
        if ratio < minimum:
            failures.append(f"{theme}: {fg} on {bg} = {ratio:.2f} < {minimum}")
    assert not failures, "\n".join(failures)


def test_forced_colors_block_preserves_color_borne_meaning():
    """Windows Contrast Themes (forced-colors: active) strip author colors.
    The stylesheet must keep the meaning color carried: discovered cells
    stay highlighted via system colors, badges keep their chip outline, and
    the theme toggle hides (both themes render as the system theme)."""
    css = CSS.read_text(encoding="utf-8")
    m = re.search(r"@media\s*\(forced-colors:\s*active\)\s*\{(.*?)\n\}", css, re.S)
    assert m, "no forced-colors media block in style.css"
    block = m.group(1)
    for required in (".known", "SelectedItem", ".badge", "#theme-toggle"):
        assert required in block, f"forced-colors block lacks {required}"


def test_no_opacity_faded_text_in_stylesheet():
    """Opacity-faded text defeats the token contrast checks above (the
    effective color depends on what's behind it). Muted text must use a
    checked token instead."""
    css = CSS.read_text(encoding="utf-8")
    faded = [m for m in re.findall(r"opacity\s*:\s*([\d.]+)", css)
             if float(m) < 1]
    assert not faded, f"opacity-faded rules present: {faded}"
