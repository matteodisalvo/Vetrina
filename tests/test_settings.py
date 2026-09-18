"""The settings file."""

from vetrina import settings


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SETTINGS_FILE", tmp_path / "Vetrina" / "settings.json")
    assert settings.load_settings() == {}
    settings.save_settings({"language": "fr", "appearance": "dark"})
    assert settings.load_settings() == {"language": "fr", "appearance": "dark"}


def test_a_broken_file_is_ignored(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("{not json")
    monkeypatch.setattr(settings, "SETTINGS_FILE", path)
    assert settings.load_settings() == {}
