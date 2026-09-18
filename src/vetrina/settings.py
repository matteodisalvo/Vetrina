"""What the app remembers between one use and the next: its language and its appearance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from . import APP_NAME

#: Where the settings are kept, as JSON.
SETTINGS_FILE = (Path.home() / "Library" / "Application Support" / APP_NAME / "settings.json"
                 if sys.platform == "darwin" else Path.home() / ".config" / APP_NAME.lower() / "settings.json")


def load_settings() -> dict:
    try:
        return json.loads(SETTINGS_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_settings(settings: dict) -> None:
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(settings))
    except OSError:
        pass  # the choice then lasts until the app closes
