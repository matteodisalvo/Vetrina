"""Drawing the card with Pillow, following the layout of GitHub's own social previews."""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .model import LABELS, LANGUAGE_COLORS, OTHER_LANGUAGE_COLOR, THEMES, Card

#: Font files tried in order, as (path, index inside a font collection).
FONT_FILES = {
    "regular": [
        ("/System/Library/Fonts/Helvetica.ttc", 0),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", 0),
        ("C:/Windows/Fonts/arial.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ],
    "bold": [
        ("/System/Library/Fonts/Helvetica.ttc", 1),
        ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 0),
        ("C:/Windows/Fonts/arialbd.ttf", 0),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 0),
    ],
}

Run = tuple[str, ImageFont.FreeTypeFont]


@lru_cache(maxsize=64)
def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """The first available font of the given weight, at ``size`` pixels."""
    for path, index in FONT_FILES[weight]:
        if Path(path).exists():
            return ImageFont.truetype(path, size, index=index)
    return ImageFont.load_default(size)


def _line_width(line: list[Run]) -> float:
    return sum(font.getlength(text) for text, font in line)


def _pieces(text: str, font: ImageFont.FreeTypeFont, width: float) -> list[str]:
    """Pieces a line may break after (spaces, hyphens, underscores, slashes), each narrower
    than ``width``: a piece wider than a whole line is cut character by character."""
    pieces = []
    for piece in (p for p in re.split(r"(?<=[\s\-_/])", text) if p):
        current = ""
        for char in piece:
            if current and font.getlength(current + char) > width:
                pieces.append(current)
                current = char
            else:
                current += char
        if current:
            pieces.append(current)
    return pieces


def _ellipsize(line: list[Run], width: float) -> list[Run]:
    """Shorten a line until it fits with a trailing ellipsis."""
    line = list(line)
    font = line[-1][1]
    while line:
        text, run_font = line[-1]
        candidate = [*line[:-1], (text.rstrip(), run_font), ("…", run_font)]
        if _line_width(candidate) <= width:
            return candidate
        line[-1] = (text[:-1], run_font)
        if not line[-1][0]:
            line.pop()
    return [("…", font)]


def wrap(runs: list[Run], width: float, max_lines: int) -> list[list[Run]]:
    """Greedy line breaking of styled text; the last line is ellipsized if text is left over."""
    lines: list[list[Run]] = [[]]
    for text, font in runs:
        for piece in _pieces(text, font, width):
            if lines[-1] and _line_width(lines[-1]) + font.getlength(piece.rstrip()) > width:
                lines.append([])
            if not lines[-1]:
                piece = piece.lstrip()
            if piece:
                lines[-1].append((piece, font))
    lines = [line for line in lines if line]
    if len(lines) <= max_lines:
        return lines
    return [*lines[: max_lines - 1], _ellipsize(lines[max_lines - 1], width)]


def draw_lines(draw: ImageDraw.ImageDraw, lines: list[list[Run]], x: float, baseline: float,
               line_height: float, fill: str) -> float:
    """Draw wrapped lines from the first baseline; returns the baseline of the last line."""
    for number, line in enumerate(lines):
        cursor = x
        for text, font in line:
            draw.text((cursor, baseline + number * line_height), text, font=font, fill=fill, anchor="ls")
            cursor += font.getlength(text)
    return baseline + (len(lines) - 1) * line_height


def draw_icon(draw: ImageDraw.ImageDraw, kind: str, cx: float, cy: float, size: float,
              color: str, width: int) -> None:
    """Simple line icons for the statistics row, centered on (cx, cy)."""
    r = size / 2
    if kind == "issues":
        draw.ellipse((cx - 0.9 * r, cy - 0.9 * r, cx + 0.9 * r, cy + 0.9 * r), outline=color, width=width)
        dot = 0.2 * r
        draw.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=color)
    elif kind == "stars":
        points = []
        for i in range(10):
            radius = r if i % 2 == 0 else 0.45 * r
            angle = math.radians(-90 + 36 * i)
            points.append((cx + radius * math.cos(angle), cy + 0.08 * r + radius * math.sin(angle)))
        draw.line([*points, points[0]], fill=color, width=width, joint="curve")
    elif kind == "forks":
        dot = 0.22 * r
        left, right, bottom = (cx - 0.55 * r, cy - 0.7 * r), (cx + 0.55 * r, cy - 0.7 * r), (cx, cy + 0.72 * r)
        for px, py in (left, right, bottom):
            draw.ellipse((px - dot, py - dot, px + dot, py + dot), outline=color, width=width)
        joint = (cx, cy + 0.1 * r)
        for px, py in (left, right):
            draw.line([(px, py + dot), (px, cy - 0.2 * r), joint], fill=color, width=width, joint="curve")
        draw.line([joint, (cx, bottom[1] - dot)], fill=color, width=width)
    elif kind == "contributors":
        for offset, scale in ((0.5 * r, 0.82), (-0.28 * r, 1.0)):  # the back person first
            x, head = cx + offset, 0.34 * r * scale
            head_y = cy - 0.42 * r * scale
            draw.ellipse((x - head, head_y - head, x + head, head_y + head), outline=color, width=width)
            body = 0.66 * r * scale
            draw.arc((x - body, cy + 0.08 * r, x + body, cy + 0.08 * r + 2 * body), 180, 360,
                     fill=color, width=width)


def render(card: Card, supersample: int = 2) -> Image.Image:
    """Draw the card. Shapes are drawn ``supersample`` times larger and scaled down, for
    smooth edges; the layout follows GitHub's cards, measured at 1200 pixels of width."""
    width, height = card.size
    W, H = width * supersample, height * supersample
    u = W / 1200  # one pixel of a 1200-pixel-wide card
    colors = THEMES[card.theme]
    image = Image.new("RGB", (W, H), colors["background"])
    draw = ImageDraw.Draw(image)

    margin, bar = 80 * u, 24 * u
    bar_top = H - bar

    # Picture in the top-right corner, with rounded corners
    text_right = W - margin
    if card.image is not None:
        side = round(200 * u)
        left, top = round(W - margin - side), round(80 * u)
        tile = Image.new("RGBA", (side, side), colors["background"])
        tile.alpha_composite(ImageOps.fit(card.image.convert("RGBA"), (side, side), Image.LANCZOS))
        mask = Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, side - 1, side - 1), radius=round(24 * u), fill=255)
        image.paste(tile.convert("RGB"), (left, top), mask)
        text_right = left - 60 * u
    text_width = text_right - margin

    # Title: owner in regular weight, repository name in bold, as on GitHub
    title_size = round(60 * u)
    regular, bold = load_font("regular", title_size), load_font("bold", title_size)
    owner, slash, name = card.title.strip().rpartition("/")
    runs = [(owner + slash, regular), (name, bold)] if slash else [(card.title.strip(), bold)]
    title_lines = wrap(runs, text_width, max_lines=2)
    baseline = 80 * u + 0.98 * title_size
    last_title_baseline = draw_lines(draw, title_lines, margin, baseline, 1.24 * title_size, colors["title"])

    # Description, as many lines as fit above the statistics
    description_size = round(32 * u)
    description_font = load_font("regular", description_size)
    line_height = 1.44 * description_size
    first = (last_title_baseline + 80 * u) if title_lines else baseline
    limit = bar_top - (150 * u if card.show_stats else 50 * u)
    max_lines = max(0, min(5, int((limit - first) // line_height) + 1))
    if card.description.strip() and max_lines:
        words = [(word + " ", description_font) for word in card.description.split()]
        lines = wrap(words, text_width, max_lines)
        draw_lines(draw, lines, margin, first, line_height, colors["text"])

    # Statistics row: icon, number and label under the number
    if card.show_stats:
        labels = LABELS[card.labels]
        contributors, issues, stars, forks = card.stats
        items = [
            ("contributors", contributors, labels[0] if contributors == 1 else labels[1]),
            ("issues", issues, labels[2]),
            ("stars", stars, labels[3]),
            ("forks", forks, labels[4]),
        ]
        number_font, label_font = load_font("regular", round(32 * u)), load_font("regular", round(24 * u))
        icon, stroke = 30 * u, max(1, round(2.6 * u))
        icon_y, number_baseline, label_baseline = bar_top - 101 * u, bar_top - 89 * u, bar_top - 51 * u
        x = margin
        for kind, value, label in items:
            number = f"{value:,}".replace(",", ".") if card.labels == "Italiano" else f"{value:,}"
            draw_icon(draw, kind, x + icon / 2, icon_y, icon, colors["text"], stroke)
            text_x = x + icon + 18 * u
            draw.text((text_x, number_baseline), number, font=number_font, fill=colors["title"], anchor="ls")
            draw.text((text_x, label_baseline), label, font=label_font, fill=colors["text"], anchor="ls")
            x = text_x + max(number_font.getlength(number), label_font.getlength(label)) + 50 * u

    # Optional text in the bottom-right corner
    if card.footer.strip():
        footer_font = load_font("bold", round(28 * u))
        draw.text((W - margin, bar_top - 51 * u), card.footer.strip(), font=footer_font,
                  fill=colors["text"], anchor="rs")

    # Bottom bar: the repository languages in proportion, or a single color
    languages = {k: v for k, v in card.languages.items() if v > 0} if card.use_language_colors else {}
    if languages:
        total, left = sum(languages.values()), 0.0
        ordered = sorted(languages.items(), key=lambda item: -item[1])
        for index, (language, size) in enumerate(ordered):
            right = W if index == len(ordered) - 1 else left + W * size / total
            draw.rectangle((round(left), bar_top, round(right), H),
                           fill=LANGUAGE_COLORS.get(language, OTHER_LANGUAGE_COLOR))
            left = right
    else:
        draw.rectangle((0, bar_top, W, H), fill=card.accent)

    return image.resize((width, height), Image.LANCZOS) if supersample > 1 else image
