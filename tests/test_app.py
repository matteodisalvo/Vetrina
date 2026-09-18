"""The window opens, loads a repository and speaks every language. Skipped without a display."""

import os
import queue
import sys

import pytest
from PIL import Image

tk = pytest.importorskip("tkinter")


def display_available() -> bool:
    if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
        return False
    try:
        tk.Tk().destroy()
    except tk.TclError:
        return False
    return True


pytestmark = pytest.mark.skipif(not display_available(), reason="needs a display")


@pytest.fixture
def window(monkeypatch):
    from vetrina.ui import app as ui

    monkeypatch.setattr(ui, "load_settings", lambda: {})
    monkeypatch.setattr(ui, "save_settings", lambda settings: None)
    window = ui.App()
    window.update()
    yield window
    window.destroy()


def test_counters_are_filled_in_from_the_start(window):
    assert window.title_counter.cget("text") == f"{len(window.card_title.get())}/60"
    assert window.description_counter.cget("text").endswith("/200")
    assert window.footer_field.counter.cget("text") == "0/40"


def test_load_and_switch_language(window):
    from vetrina.i18n import LANGUAGES

    results = queue.Queue()
    results.put({"title": "octo/demo", "description": "A demo", "stats": (12, 3, 4567, 89),
                 "languages": {"Python": 10}, "image": Image.new("RGB", (40, 40), "red")})
    window._wait_for(results)
    window.refresh()
    assert window._rendered.size == (1280, 640)
    for language in LANGUAGES:
        window.set_language(language)
        window.update()
        assert window.language == language
        assert window.card_title.get() == "octo/demo"
    assert window.picture is not None
