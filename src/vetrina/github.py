"""Reading a public repository from the GitHub API, without a token."""

from __future__ import annotations

import io
import json
import re
import ssl
import urllib.error
import urllib.request

import certifi
from PIL import Image

#: The certificates to trust come with certifi: the Python inside the built apps would look
#: for them where the machine that built it kept them, which is not there on other computers.
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class LoadError(Exception):
    """A repository that could not be loaded. ``key`` names the message in i18n.py,
    and ``values`` fill it in, so the window shows it in its own language."""

    def __init__(self, key: str, **values: object) -> None:
        super().__init__(key)
        self.key, self.values = key, values


def parse_repository(text: str) -> tuple[str, str]:
    """Owner and name from ``owner/name`` or from any github.com link to the repository."""
    cleaned = re.sub(r"^(https?://)?(www\.)?github\.com/", "", text.strip())
    parts = re.sub(r"\.git$", "", cleaned.strip("/")).split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise LoadError("error_format")
    return parts[0], parts[1]


def _open(url: str):
    headers = {"User-Agent": "vetrina", "Accept": "application/vnd.github+json"}
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15, context=SSL_CONTEXT)


def fetch_repository(text: str) -> dict:
    """Title, description, statistics, languages and owner avatar of a public repository."""
    owner, name = parse_repository(text)
    api = f"https://api.github.com/repos/{owner}/{name}"
    try:
        with _open(api) as response:
            repo = json.load(response)
        with _open(api + "/languages") as response:
            languages = json.load(response)
        with _open(api + "/contributors?per_page=1&anon=1") as response:
            link, body = response.headers.get("Link", ""), response.read()
        last_page = re.search(r'[?&]page=(\d+)>; rel="last"', link)
        contributors = int(last_page.group(1)) if last_page else (len(json.loads(body)) if body else 0)
        avatar_url = repo["owner"]["avatar_url"]
        with _open(avatar_url + ("&" if "?" in avatar_url else "?") + "s=400") as response:
            avatar = Image.open(io.BytesIO(response.read()))
            avatar.load()
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise LoadError("error_not_found", repository=f"{owner}/{name}") from error
        if error.code in (403, 429):
            raise LoadError("error_rate_limited") from error
        raise LoadError("error_http", code=error.code) from error
    except urllib.error.URLError as error:
        raise LoadError("error_offline") from error
    return {
        "title": repo["full_name"],
        "description": repo.get("description") or "",
        "stats": (contributors, repo.get("open_issues_count", 0), repo.get("stargazers_count", 0),
                  repo.get("forks_count", 0)),
        "languages": languages,
        "image": avatar,
    }
