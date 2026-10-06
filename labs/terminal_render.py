"""Render terminal text outputs into clean dark-mode terminal card PNGs.

Used by lab scripts to produce publication-ready proof artifacts.
"""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BG_COLOR = (15, 21, 26)
BORDER_COLOR = (35, 45, 55)
TOPBAR_COLOR = (20, 27, 34)
DOT_RED = (255, 95, 86)
DOT_YELLOW = (255, 189, 46)
DOT_GREEN = (39, 201, 63)

COLOR_DEFAULT = (224, 231, 237)
COLOR_MUTED = (110, 125, 138)
COLOR_GREEN = (62, 180, 78)
COLOR_RED = (248, 81, 73)
COLOR_BLUE = (118, 187, 248)
COLOR_YELLOW = (235, 178, 60)
COLOR_WHITE = (245, 248, 250)


def _get_font(size: int = 14) -> ImageFont.FreeTypeFont:
    candidate_fonts = [
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/SFMono-Regular.otf",
        "/System/Library/Fonts/Monaco.dfont",
        "/Library/Fonts/Courier New.ttf",
    ]
    for path in candidate_fonts:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_terminal(
    title: str,
    lines: list[tuple[str, str]],  # (text, color_key)
    out_path: str | Path,
    width: int = 1100,
    height: int = 416,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (width, height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Outer border
    draw.rectangle([(0, 0), (width - 1, height - 1)], outline=BORDER_COLOR, width=1)

    # Top title bar
    bar_height = 36
    draw.rectangle([(1, 1), (width - 2, bar_height)], fill=TOPBAR_COLOR)
    draw.line([(1, bar_height), (width - 2, bar_height)], fill=BORDER_COLOR, width=1)

    # macOS window controls
    dot_y = bar_height // 2
    for idx, col in enumerate([DOT_RED, DOT_YELLOW, DOT_GREEN]):
        cx = 24 + idx * 18
        draw.ellipse([(cx - 5, dot_y - 5), (cx + 5, dot_y + 5)], fill=col)

    # Title in top bar
    bar_font = _get_font(12)
    t_bbox = draw.textbbox((0, 0), title, font=bar_font)
    tw = t_bbox[2] - t_bbox[0]
    draw.text(((width - tw) // 2, dot_y - 7), title, fill=COLOR_MUTED, font=bar_font)

    # Content
    font = _get_font(14)
    line_height = 22
    start_y = bar_height + 20
    start_x = 32

    colors = {
        "default": COLOR_DEFAULT,
        "muted": COLOR_MUTED,
        "green": COLOR_GREEN,
        "red": COLOR_RED,
        "blue": COLOR_BLUE,
        "yellow": COLOR_YELLOW,
        "white": COLOR_WHITE,
    }

    cur_y = start_y
    for text, c_key in lines:
        if cur_y + line_height > height - 12:
            break
        c = colors.get(c_key, COLOR_DEFAULT)
        draw.text((start_x, cur_y), text, fill=c, font=font)
        cur_y += line_height

    img.save(out_path, "PNG")
    return out_path
