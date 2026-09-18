"""The translations: complete, consistent, and covering every text the code asks for."""

import re
from pathlib import Path

import pytest

import vetrina
from vetrina.i18n import LANGUAGES, TEXTS, translate


@pytest.mark.parametrize("key", sorted(TEXTS))
def test_every_language_has_the_text(key):
    assert set(TEXTS[key]) == set(LANGUAGES)


@pytest.mark.parametrize("key", sorted(TEXTS))
def test_every_language_fills_in_the_same_values(key):
    fields = {language: sorted(re.findall(r"\{(\w+)\}", text)) for language, text in TEXTS[key].items()}
    assert len({tuple(names) for names in fields.values()}) == 1, fields


def test_every_text_the_code_asks_for_exists():
    source = "\n".join(path.read_text() for path in Path(vetrina.__file__).parent.rglob("*.py"))
    asked = set()
    for pattern in (r'\bt\(\s*"(\w+)"', r'set_status\(\s*"(\w+)"', r'LoadError\(\s*"(\w+)"'):
        asked |= set(re.findall(pattern, source))
    assert asked - set(TEXTS) == set()


def test_values_are_filled_in_and_english_is_the_fallback():
    assert translate("it", "status_saved", path="/x.png") == "Salvata in /x.png"
    assert translate("xx", "load") == TEXTS["load"]["en"]
