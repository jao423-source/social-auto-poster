#!/usr/bin/env python3
"""
Generates a branded quote-card image (1600x1600, Instagram/Facebook square)
for a single post. No network access required — pure local rendering.

Usage:
    python3 generate_image.py --text "Quote text here" --out output.png
    python3 generate_image.py --text "..." --attribution "@yourhandle" --out output.png
"""
import argparse
import json
import textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).parent
THEME_PATH = SCRIPT_DIR / "theme.json"

CANVAS = 1600
MARGIN = 140

# Fonts are bundled in ../fonts (not relying on system fonts, so rendering
# is identical here and on the GitHub Actions runner).
FONTS_DIR = SCRIPT_DIR.parent / "fonts"
SERIF_VARIABLE = str(FONTS_DIR / "Lora-Variable.ttf")
SANS = str(FONTS_DIR / "Poppins-Medium.ttf")
SANS_LIGHT = str(FONTS_DIR / "Poppins-Regular.ttf")


def truetype_bold_serif(size):
    font = ImageFont.truetype(SERIF_VARIABLE, size)
    try:
        font.set_variation_by_name("Bold")
    except Exception:
        pass
    return font


def load_theme():
    if THEME_PATH.exists():
        return json.loads(THEME_PATH.read_text())
    # Sensible default theme (deep ink ground, warm off-white text, single accent).
    return {
        "bg": "#171B26",
        "text": "#F4F1EA",
        "muted": "#9099AC",
        "accent": "#D98E4A",
        "label": "YOUR PAGE"
    }


def fit_font(draw, text, font_loader, max_width, max_height, start_size, min_size=44):
    """Binary-search the largest font size whose wrapped text fits the box."""
    size = start_size
    while size > min_size:
        font = font_loader(size)
        avg_char_w = font.getlength("n")
        wrap_width = max(10, int(max_width / max(avg_char_w, 1)))
        lines = textwrap.wrap(text, width=wrap_width, break_long_words=False)
        line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
        total_h = len(lines) * line_h * 1.3
        widest = max((draw.textlength(l, font=font) for l in lines), default=0)
        if total_h <= max_height and widest <= max_width:
            return font, lines, line_h * 1.3
        size -= 4
    font = font_loader(min_size)
    wrap_width = max(10, int(max_width / max(font.getlength("n"), 1)))
    lines = textwrap.wrap(text, width=wrap_width, break_long_words=False)
    line_h = font.getbbox("Ag")[3] - font.getbbox("Ag")[1]
    return font, lines, line_h * 1.3


def generate(text: str, out_path: str, attribution: str = "", theme: dict = None):
    theme = theme or load_theme()
    img = Image.new("RGB", (CANVAS, CANVAS), theme["bg"])
    draw = ImageDraw.Draw(img)

    content_w = CANVAS - 2 * MARGIN
    content_h = CANVAS - 2 * MARGIN - 160  # leave room for label + rule at bottom

    quote_text = f"“{text.strip()}”"
    font, lines, line_h = fit_font(draw, quote_text, truetype_bold_serif, content_w, content_h, start_size=112)

    total_text_h = len(lines) * line_h
    y = (CANVAS - total_text_h) / 2 - 40

    for line in lines:
        w = draw.textlength(line, font=font)
        x = (CANVAS - w) / 2
        draw.text((x, y), line, font=font, fill=theme["text"])
        y += line_h

    # Accent rule
    rule_w = 90
    rule_y = CANVAS - MARGIN - 70
    draw.rectangle(
        [(CANVAS - rule_w) / 2, rule_y, (CANVAS + rule_w) / 2, rule_y + 5],
        fill=theme["accent"],
    )

    # Bottom label / attribution
    label_font = ImageFont.truetype(SANS, 34)
    label = attribution.upper() if attribution else theme.get("label", "")
    if label:
        lw = draw.textlength(label, font=label_font)
        draw.text(((CANVAS - lw) / 2, rule_y + 30), label, font=label_font, fill=theme["muted"])

    img.save(out_path, "PNG")
    return out_path


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--attribution", default="")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    generate(args.text, args.out, args.attribution)
    print(f"Wrote {args.out}")
