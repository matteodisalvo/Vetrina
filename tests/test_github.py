"""Reading repositories: every way people write one, and every way GitHub can answer."""

import io
import json
import urllib.error

import pytest
from PIL import Image

from vetrina import github
from vetrina.github import LoadError, fetch_repository, parse_repository


@pytest.fixture(autouse=True)
def fresh_cache():
    github._cache.clear()  # every test asks GitHub again


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


def fake_github(url: str, token: str = "") -> FakeResponse:
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
    def failing(url, token=""):
        raise error

    monkeypatch.setattr(github, "_open", failing)
    with pytest.raises(LoadError) as raised:
        fetch_repository("octo/demo")
    assert raised.value.key == key


def test_logo_shown_in_the_readme_comes_first():
    readme = ('<p align="center"><img src="assets/logo/demo-1024.png" width="112"></p>\n'
              "![shot](docs/shot.png) ![build](https://img.shields.io/badge/logo-blue.png)")
    assert github.logo_candidates(readme, "octo", "demo")[0] == "assets/logo/demo-1024.png"
    readme = "![logo](https://raw.githubusercontent.com/octo/demo/main/docs/logo.png?raw=true)"
    assert github.logo_candidates(readme, "octo", "demo")[0] == "docs/logo.png"
    readme = "![logo](https://example.com/img/demo-logo.png)"
    assert github.logo_candidates(readme, "octo", "demo")[0] == "https://example.com/img/demo-logo.png"


def test_without_a_logo_in_the_readme_the_usual_places_are_tried():
    readme = "![logo](art/logo.svg) ![shot](docs/screenshot.png) ![x](tests/fixtures/logo.png)"
    candidates = github.logo_candidates(readme, "octo", "demo")
    assert candidates[:3] == ["logo.png", "icon.png", "assets/logo.png"]
    assert all(not path.endswith(".svg") and not path.startswith("tests/") for path in candidates)


def logo_github(size: tuple[int, int], seen: list | None = None):
    def fake(url: str, token: str = "") -> FakeResponse:
        if seen is not None:
            seen.append((url, token))
        if url.startswith("https://raw.githubusercontent.com/octo/demo/main/"):
            path = url.rpartition("/main/")[2]
            if path == "README.md":
                return FakeResponse(b"# Demo")
            if path == "assets/logo.png":
                picture = io.BytesIO()
                Image.new("RGB", size, "blue").save(picture, "PNG")
                return FakeResponse(picture.getvalue())
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        if url == "https://api.github.com/repos/octo/demo":
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


def test_a_load_asks_the_api_three_times_and_then_nothing_for_an_hour(monkeypatch):
    seen = []
    monkeypatch.setattr(github, "_open", logo_github((20, 20), seen))
    fetch_repository("octo/demo")
    assert len([url for url, _ in seen if url.startswith(github.API)]) == 3
    seen.clear()
    assert fetch_repository("https://github.com/Octo/Demo")["title"] == "octo/demo"
    assert seen == []


def test_the_token_goes_only_to_the_api(monkeypatch):
    requests = []
    monkeypatch.setattr(github.urllib.request, "urlopen", lambda request, **_: requests.append(request))
    github._open("https://api.github.com/repos/octo/demo", "secret")
    github._open("https://raw.githubusercontent.com/octo/demo/main/logo.png", "secret")
    assert requests[0].get_header("Authorization") == "Bearer secret"
    assert requests[1].get_header("Authorization") is None


def test_a_refused_token_is_left_out(monkeypatch):
    seen = []
    answer = logo_github((20, 20), seen)

    def refusing(url, token=""):
        if token:
            raise urllib.error.HTTPError(url, 401, "Bad credentials", {}, None)
        return answer(url, token)

    monkeypatch.setattr(github, "_open", refusing)
    repository = fetch_repository("octo/demo", "wrong")
    assert repository["token_refused"] and repository["title"] == "octo/demo"


def test_the_limit_says_until_when(monkeypatch):
    def limited(url, token=""):
        raise urllib.error.HTTPError(url, 403, "Forbidden", {"X-RateLimit-Reset": "0"}, None)

    monkeypatch.setattr(github, "_open", limited)
    with pytest.raises(LoadError) as raised:
        fetch_repository("octo/demo")
    assert raised.value.key == "error_rate_limited"
    assert raised.value.values["time"] == github.time.strftime("%H:%M", github.time.localtime(0))


def test_where_the_token_comes_from(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(github, "_cli_token", lambda: "from-cli")
    assert github.find_token(" saved ") == "saved"
    assert github.find_token() == "from-cli"
    monkeypatch.setenv("GH_TOKEN", "from-env")
    assert github.find_token() == "from-env"
    monkeypatch.setattr(github, "_cli_token", lambda: "")
    monkeypatch.delenv("GH_TOKEN")
    assert github.find_token() == ""


def test_certificates_come_with_the_app():
    # The built apps cannot rely on the certificates of the machine that built them
    assert github.SSL_CONTEXT.cert_store_stats()["x509_ca"] > 100
