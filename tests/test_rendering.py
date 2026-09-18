"""Drawing the card."""

import pytest
from PIL import Image

from vetrina.model import LANGUAGE_COLORS, PRESETS, Card
from vetrina.rendering import load_font, render, wrap


@pytest.mark.parametrize("size", PRESETS.values())
def test_size_of_every_format(size):
    assert render(Card(size=size), supersample=1).size == size


def test_everything_at_once():
    card = Card(title="owner/" + "a-long-name-" * 12, description="word " * 300, image=Image.new("RGBA", (50, 30)),
                languages={"Python": 3, "A language without a color": 1}, footer="example.com", theme="Scuro",
                labels="Italiano", stats=(1, 2, 3000, 4))
    image = render(card)
    assert image.size == card.size
    assert image.mode == "RGB"


def test_bar_of_a_single_color():
    card = Card(use_language_colors=False, accent="#ff0000")
    assert render(card, supersample=1).getpixel((10, card.size[1] - 5)) == (255, 0, 0)


def test_bar_of_the_languages():
    card = Card(languages={"Python": 1})
    color = LANGUAGE_COLORS["Python"]
    expected = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    assert render(card, supersample=1).getpixel((10, card.size[1] - 5)) == expected


def test_wrap_stops_at_the_last_line_with_an_ellipsis():
    font = load_font("regular", 20)
    lines = wrap([("word " * 100, font)], width=200, max_lines=3)
    assert len(lines) == 3
    assert lines[-1][-1][0] == "…"
    assert all(sum(run_font.getlength(text) for text, run_font in line) <= 200 for line in lines)


def test_wrap_cuts_words_longer_than_a_line():
    font = load_font("bold", 20)
    lines = wrap([("x" * 200, font)], width=100, max_lines=10)
    assert all(sum(run_font.getlength(text) for text, run_font in line) <= 100 for line in lines)
