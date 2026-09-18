"""Pillow helpers for the window: opening pictures, rounding them, lifting the preview."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


def open_image(path: Path) -> Image.Image | None:
    """The image at ``path``, or None when it is missing: the app works without its logo."""
    try:
        image = Image.open(path)
        image.load()
    except OSError:
        return None
    return image


def rounded_picture(picture: Image.Image, side: int, radius: int) -> Image.Image:
    """A square crop of ``picture`` with transparent rounded corners, drawn at twice the
    size and scaled down for smooth corners."""
    tile = ImageOps.fit(picture.convert("RGBA"), (2 * side, 2 * side), Image.LANCZOS)
    mask = Image.new("L", tile.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 2 * side - 1, 2 * side - 1), radius=2 * radius, fill=255)
    tile.putalpha(ImageChops.multiply(tile.getchannel("A"), mask))
    return tile.resize((side, side), Image.LANCZOS)


@lru_cache(maxsize=4)
def card_shadow(width: int, height: int, pad: int) -> Image.Image:
    """The soft shadow under a card of the given size, as a mask with ``pad`` pixels around it."""
    mask = Image.new("L", (width + 2 * pad, height + 2 * pad), 0)
    ImageDraw.Draw(mask).rectangle((pad, pad + 6, pad + width, pad + height + 6), fill=56)
    return mask.filter(ImageFilter.GaussianBlur(10))


def with_shadow(card: Image.Image, ground: str, edge: str, pad: int) -> Image.Image:
    """``card`` on a ``ground`` colored backdrop, lifted by a soft shadow and edged by a hairline."""
    backdrop = Image.new("RGB", (card.width + 2 * pad, card.height + 2 * pad), ground)
    backdrop.paste((0, 0, 0), (0, 0, *backdrop.size), card_shadow(card.width, card.height, pad))
    ImageDraw.Draw(backdrop).rectangle((pad - 1, pad - 1, pad + card.width, pad + card.height), outline=edge)
    backdrop.paste(card, (pad, pad))
    return backdrop
