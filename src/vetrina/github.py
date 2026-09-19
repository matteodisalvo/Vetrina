"""Reading a public repository from the GitHub API.

Without a token GitHub answers 60 requests an hour from each connection, and loading a
repository takes 3 of them: pictures come from raw.githubusercontent.com, which does not
count, and a repository loaded again within the hour is not asked for at all. With a token
(saved in the app, in GITHUB_TOKEN or GH_TOKEN, or the GitHub CLI's) the limit is 5,000.
"""

from __future__ import annotations

import io
import json
import os
import posixpath
import re
import shutil
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

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


API = "https://api.github.com/"
#: Where the GitHub CLI is installed, for an app opened from the Finder, which gets no PATH.
GH_LOCATIONS = ("/opt/homebrew/bin/gh", "/usr/local/bin/gh")
#: A repository loaded again within this many seconds is taken from memory, not from GitHub.
CACHE_SECONDS = 3600
_cache: dict[str, tuple[float, dict]] = {}


def _open(url: str, token: str = ""):
    headers = {"User-Agent": "vetrina", "Accept": "application/vnd.github+json"}
    if token and url.startswith(API):  # the token only ever goes to GitHub's API
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15, context=SSL_CONTEXT)


@lru_cache(maxsize=1)
def _cli_token() -> str:
    gh = shutil.which("gh") or next((path for path in GH_LOCATIONS if os.path.exists(path)), None)
    if gh is None:
        return ""
    try:
        result = subprocess.run([gh, "auth", "token"], capture_output=True, text=True, timeout=5,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def find_token(saved: str = "") -> str:
    """The GitHub token to use: the one saved in the app, else GITHUB_TOKEN or GH_TOKEN, else
    the GitHub CLI's when it is installed and signed in. Empty without any."""
    for token in (saved, os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_TOKEN")):
        if token and token.strip():
            return token.strip()
    return _cli_token()


#: Pictures Pillow can open; an SVG logo is left out, and the owner's picture is used instead.
PICTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_PICTURE_BYTES = 5_000_000
#: Folders whose pictures belong to other projects or to tests, not to the project itself.
SKIPPED_FOLDERS = {"node_modules", "vendor", "third_party", "test", "tests", "__tests__", "fixtures", "examples"}
#: Where projects often keep their logo, tried after the logos their README shows.
LOGO_FOLDERS = ("", "assets/", "docs/", ".github/", "images/", "img/")
LOGO_FILES = ("logo.png", "icon.png")
README_FILES = ("README.md", "readme.md", "README.rst", "README")
README_PICTURE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)|<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)", re.IGNORECASE)


def _picture_source(source: str, owner: str, name: str) -> str:
    """A picture of the README as a path inside the repository (for a relative path, or a link
    to the repository's own files) or as a full link to another site. Empty when it is not
    a picture Pillow can open, or when it is a badge."""
    source = source.strip()
    link = urllib.parse.urlsplit(source)
    path = urllib.parse.unquote(link.path)
    if not path.lower().endswith(PICTURE_EXTENSIONS):
        return ""
    if link.scheme or link.netloc:
        own = re.match(rf"(?:/{re.escape(owner)}/{re.escape(name)}/(?:blob/|raw/)?[^/]+)/(.+)", path, re.IGNORECASE)
        if own and link.netloc.lower() in ("raw.githubusercontent.com", "github.com", "www.github.com"):
            return own.group(1)
        if link.scheme != "https" or "badge" in source.lower() or "shields.io" in link.netloc.lower():
            return ""
        return urllib.parse.urlunsplit((link.scheme, link.netloc, link.path, link.query, ""))
    return posixpath.normpath(path.lstrip("/")).lstrip("./") if path.strip("./") else ""


def logo_candidates(readme: str, owner: str, name: str) -> list[str]:
    """Pictures that may be the project's logo, best first, as paths inside the repository or
    as links: the logos and icons its README shows, then the places where projects often keep
    one."""
    shown = []
    for match in README_PICTURE.finditer(readme):
        source = _picture_source(match.group(1) or match.group(2), owner, name)
        external = "://" in source
        where = urllib.parse.urlsplit(source).path.lower() if external else source.lower()
        folders = where.split("/")[:-1]
        if (source and source not in shown and not SKIPPED_FOLDERS.intersection(folders)
                and ("logo" in where or (not external and "icon" in where))):
            shown.append(source)
    usual = [folder + file for folder in LOGO_FOLDERS for file in LOGO_FILES]
    return shown[:3] + [path for path in usual if path not in shown[:3]]


def _download(url: str) -> bytes | None:
    """The file at ``url``, or None when it is missing, unreachable or too big for a picture."""
    try:
        with _open(url) as response:
            data = response.read(MAX_PICTURE_BYTES + 1)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return data if len(data) <= MAX_PICTURE_BYTES else None


def _raw_url(full_name: str, branch: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{full_name}/{urllib.parse.quote(branch)}/{urllib.parse.quote(path)}"


def _square_enough(data: bytes | None) -> Image.Image | None:
    """The picture in ``data`` when it fits the square of the card: a long logo with its name
    written out would be cut off."""
    if data is None:
        return None
    try:
        picture = Image.open(io.BytesIO(data))
        picture.load()
    except (OSError, ValueError, Image.DecompressionBombError):
        return None
    return picture if picture.width <= 2 * picture.height and picture.height <= 2 * picture.width else None


def _project_logo(full_name: str, branch: str) -> tuple[Image.Image, str] | None:
    """The project's logo and its file name, when the repository has one the card can show.
    Everything comes from raw.githubusercontent.com, outside the limit of the API."""
    owner, name = full_name.split("/")
    readme = ""
    for file in README_FILES:
        data = _download(_raw_url(full_name, branch, file))
        if data is not None:
            readme = data.decode("utf-8", "replace")
            break
    candidates = logo_candidates(readme, owner, name)
    urls = [source if "://" in source else _raw_url(full_name, branch, source) for source in candidates]
    with ThreadPoolExecutor(max_workers=8) as pool:  # the missing ones answer quickly, all together
        pictures = list(pool.map(lambda url: _square_enough(_download(url)), urls))
    for source, picture in zip(candidates, pictures, strict=True):
        if picture is not None:
            return picture, posixpath.basename(urllib.parse.urlsplit(source).path)
    return None


def _until(error: urllib.error.HTTPError) -> str:
    """When GitHub will answer again after limiting the requests, as hours and minutes."""
    headers = error.headers or {}
    if headers.get("X-RateLimit-Reset", "").isdigit():
        moment = int(headers["X-RateLimit-Reset"])
    elif headers.get("Retry-After", "").isdigit():
        moment = time.time() + int(headers["Retry-After"])
    else:
        moment = time.time() + 3600
    return time.strftime("%H:%M", time.localtime(moment))


def fetch_repository(text: str, token: str = "") -> dict:
    """Title, description, statistics, languages and picture of a public repository: its logo
    when it has one, else its owner's avatar. A token GitHub refuses is left out, and the
    result then says so in ``token_refused``."""
    owner, name = parse_repository(text)
    key = f"{owner}/{name}".lower()
    cached = _cache.get(key)
    if cached is not None and time.monotonic() - cached[0] < CACHE_SECONDS:
        return dict(cached[1])
    try:
        repository = _fetch(owner, name, token)
    except LoadError as error:
        if not (token and error.key == "error_http" and error.values.get("code") == 401):
            raise
        repository = {**_fetch(owner, name, ""), "token_refused": True}
    _cache[key] = (time.monotonic(), repository)
    return dict(repository)


def _fetch(owner: str, name: str, token: str) -> dict:
    api = f"{API}repos/{owner}/{name}"
    try:
        with _open(api, token) as response:
            repo = json.load(response)
        with _open(api + "/languages", token) as response:
            languages = json.load(response)
        with _open(api + "/contributors?per_page=1&anon=1", token) as response:
            link, body = response.headers.get("Link", ""), response.read()
        last_page = re.search(r'[?&]page=(\d+)>; rel="last"', link)
        contributors = int(last_page.group(1)) if last_page else (len(json.loads(body)) if body else 0)
        logo = _project_logo(repo["full_name"], repo["default_branch"]) if repo.get("default_branch") else None
        if logo is not None:
            picture, picture_name = logo
        else:
            avatar_url = repo["owner"]["avatar_url"]
            with _open(avatar_url + ("&" if "?" in avatar_url else "?") + "s=400") as response:
                picture = Image.open(io.BytesIO(response.read()))
                picture.load()
            picture_name = ""
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise LoadError("error_not_found", repository=f"{owner}/{name}") from error
        if error.code in (403, 429):
            raise LoadError("error_rate_limited", time=_until(error)) from error
        raise LoadError("error_http", code=error.code) from error
    except urllib.error.URLError as error:
        raise LoadError("error_offline") from error
    return {
        "title": repo["full_name"],
        "description": repo.get("description") or "",
        "stats": (contributors, repo.get("open_issues_count", 0), repo.get("stargazers_count", 0),
                  repo.get("forks_count", 0)),
        "languages": languages,
        "image": picture,
        "image_name": picture_name,  # the logo's file name; empty for the owner's picture
    }
