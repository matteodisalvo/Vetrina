"""Reading repositories: every way people write one, and every way GitHub can answer."""

import io
import json
import urllib.error

import pytest
from PIL import Image

from vetrina import github
from vetrina.github import LoadError, fetch_repository, parse_repository


@pytest.mark.parametrize("text", [
    "matteodisalvo/vetrina",
    "  matteodisalvo/vetrina  ",
    "https://github.com/matteodisalvo/vetrina",
    "http://www.github.com/matteodisalvo/vetrina/",
    "github.com/matteodisalvo/vetrina.git",
    "https://github.com/matteodisalvo/vetrina/tree/main/src",
])
def test_repository_forms(text):
    assert parse_repository(text) == ("matteodisalvo", "vetrina")


@pytest.mark.parametrize("text", ["", "vetrina", "https://github.com/matteodisalvo", "/", "owner/"])
def test_bad_repository(text):
    with pytest.raises(LoadError) as error:
        parse_repository(text)
    assert error.value.key == "error_format"


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes, headers: dict | None = None):
        super().__init__(data)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def fake_github(url: str) -> FakeResponse:
    if url.endswith("/languages"):
        return FakeResponse(json.dumps({"Python": 90, "Shell": 10}).encode())
    if "/contributors" in url:
        link = '<https://api.github.com/repositories/1/contributors?per_page=1&anon=1&page=12>; rel="last"'
        return FakeResponse(b"[{}]", {"Link": link})
    if "avatars" in url:
        picture = io.BytesIO()
        Image.new("RGB", (8, 8), "red").save(picture, "PNG")
        return FakeResponse(picture.getvalue())
    return FakeResponse(json.dumps({
        "full_name": "octo/demo", "description": "A demo", "open_issues_count": 3, "stargazers_count": 4567,
        "forks_count": 89, "owner": {"avatar_url": "https://avatars.example/u/1?v=4"},
    }).encode())


def test_fetch(monkeypatch):
    monkeypatch.setattr(github, "_open", fake_github)
    repository = fetch_repository("octo/demo")
    assert repository["title"] == "octo/demo"
    assert repository["description"] == "A demo"
    assert repository["stats"] == (12, 3, 4567, 89)
    assert repository["languages"] == {"Python": 90, "Shell": 10}
    assert repository["image"].size == (8, 8)


@pytest.mark.parametrize(("error", "key"), [
    (urllib.error.HTTPError("url", 404, "Not Found", {}, None), "error_not_found"),
    (urllib.error.HTTPError("url", 403, "Forbidden", {}, None), "error_rate_limited"),
    (urllib.error.HTTPError("url", 500, "Server Error", {}, None), "error_http"),
    (urllib.error.URLError("offline"), "error_offline"),
])
def test_fetch_errors(monkeypatch, error, key):
    def failing(url):
        raise error

    monkeypatch.setattr(github, "_open", failing)
    with pytest.raises(LoadError) as raised:
        fetch_repository("octo/demo")
    assert raised.value.key == key
