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
    assert repository["image_name"] == ""  # no logo in the repository: the owner's picture


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


def test_certificates_come_with_the_app():
    # The built apps cannot rely on the certificates of the machine that built them
    assert github.SSL_CONTEXT.cert_store_stats()["x509_ca"] > 100


def test_logo_shown_in_the_readme_comes_first():
    files = {"README.md": 900, "assets/logo/demo-1024.png": 50_000, "assets/logo/demo-icon.png": 40_000,
             "docs/logo.png": 30_000}
    readme = '<p align="center"><img src="assets/logo/demo-1024.png" width="112"></p>\n![shot](docs/shot.png)'
    assert github.logo_candidates(files, readme, "octo", "demo")[0] == "assets/logo/demo-1024.png"
    readme = "![logo](https://raw.githubusercontent.com/octo/demo/main/docs/logo.png?raw=true)"
    assert github.logo_candidates(files, readme, "octo", "demo")[0] == "docs/logo.png"


def test_logo_found_by_its_name():
    files = {"README.md": 900, "docs/screenshot.png": 90_000, "src/app/icon.png": 8_000,
             "branding/demo-logo.png": 20_000, "tests/fixtures/logo.png": 500, "node_modules/x/logo.png": 900,
             "art/logo.svg": 3_000, "docs/huge-logo.png": 9_000_000}
    candidates = github.logo_candidates(files, "", "octo", "demo")
    assert candidates == ["branding/demo-logo.png", "src/app/icon.png"]
    assert github.logo_candidates({"docs/photo.png": 10}, "", "octo", "demo") == []


def logo_github(size: tuple[int, int]):
    def fake(url: str) -> FakeResponse:
        if "/git/trees/" in url:
            return FakeResponse(json.dumps({"tree": [
                {"path": "README.md", "type": "blob", "size": 40},
                {"path": "assets", "type": "tree"},
                {"path": "assets/logo.png", "type": "blob", "size": 100},
            ]}).encode())
        if url.endswith("/README.md"):
            return FakeResponse(b"# Demo")
        if url.endswith("/assets/logo.png"):
            picture = io.BytesIO()
            Image.new("RGB", size, "blue").save(picture, "PNG")
            return FakeResponse(picture.getvalue())
        if url.startswith("https://api.github.com/repos/octo/demo") and "/" not in url.rpartition("demo")[2]:
            return FakeResponse(json.dumps({
                "full_name": "octo/demo", "description": "A demo", "default_branch": "main",
                "owner": {"avatar_url": "https://avatars.example/u/1?v=4"},
            }).encode())
        return fake_github(url)
    return fake


def test_fetch_uses_the_project_logo(monkeypatch):
    monkeypatch.setattr(github, "_open", logo_github((20, 20)))
    repository = fetch_repository("octo/demo")
    assert repository["image_name"] == "logo.png"
    assert repository["image"].size == (20, 20)


def test_a_long_logo_is_left_for_the_owner_picture(monkeypatch):
    monkeypatch.setattr(github, "_open", logo_github((90, 20)))
    repository = fetch_repository("octo/demo")
    assert repository["image_name"] == ""
    assert repository["image"].size == (8, 8)
