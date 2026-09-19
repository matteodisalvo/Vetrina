"""Reading a public repository from the GitHub API, without a token."""

from __future__ import annotations

import io
import json
import posixpath
import re
import ssl
import urllib.error
import urllib.parse
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


#: Pictures Pillow can open; an SVG logo is left out, and the owner's picture is used instead.
PICTURE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
MAX_PICTURE_BYTES = 5_000_000
MAX_LOGO_TRIES = 3
#: Folders whose pictures belong to other projects or to tests, not to the project itself.
SKIPPED_FOLDERS = {"node_modules", "vendor", "third_party", "test", "tests", "__tests__", "fixtures", "examples"}
README_PICTURE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)|<img\b[^>]*?\bsrc\s*=\s*[\"']([^\"']+)", re.IGNORECASE)


def _path_in_repository(source: str, owner: str, name: str) -> str:
    """The path inside the repository of a picture in its README: relative, or a link to this
    repository's files on github.com or raw.githubusercontent.com. Empty for anything else."""
    source = urllib.parse.unquote(source.split("#")[0].split("?")[0])
    if re.match(r"[a-z]+:", source, re.IGNORECASE):
        link = re.match(rf"https?://(?:raw\.githubusercontent\.com/{re.escape(owner)}/{re.escape(name)}/[^/]+"
                        rf"|github\.com/{re.escape(owner)}/{re.escape(name)}/(?:blob|raw)/[^/]+)/(.+)",
                        source, re.IGNORECASE)
        return link.group(1) if link else ""
    return posixpath.normpath(source.lstrip("/")).lstrip("./") if source.strip("./") else ""


def _logo_score(path: str, name: str) -> float:
    """How much ``path`` looks like the project's logo: 0 when it does not at all."""
    *folders, file = path.lower().split("/")
    stem = file.rpartition(".")[0]
    if SKIPPED_FOLDERS.intersection(folders) or any(word in stem for word in ("banner", "screenshot", "badge")):
        return 0
    score = (4 * ("logo" in stem) + 3 * any("logo" in folder for folder in folders)
             + (1 if "favicon" in stem else 2 * ("icon" in stem)))
    return score + (name.lower() in stem) - 0.1 * len(folders) if score else 0


def logo_candidates(files: dict[str, int], readme: str, owner: str, name: str) -> list[str]:
    """Paths among ``files`` (path -> size in bytes) that may be the project's logo, best first:
    the logos and icons the README shows, then the files whose name and folders say "logo" or
    "icon" the most."""
    pictures = {path: size for path, size in files.items()
                if path.lower().endswith(PICTURE_EXTENSIONS) and size <= MAX_PICTURE_BYTES}
    shown = []
    for match in README_PICTURE.finditer(readme):
        path = _path_in_repository(match.group(1) or match.group(2), owner, name)
        if path in pictures and ("logo" in path.lower() or "icon" in path.lower()) and path not in shown:
            shown.append(path)
    scored = sorted(((_logo_score(path, name), size, path) for path, size in pictures.items()), reverse=True)
    return shown + [path for score, _, path in scored if score > 0 and path not in shown]


def _raw(full_name: str, branch: str, path: str) -> bytes:
    url = (f"https://raw.githubusercontent.com/{full_name}/{urllib.parse.quote(branch)}/"
           f"{urllib.parse.quote(path)}")
    with _open(url) as response:
        return response.read()


def _project_logo(full_name: str, branch: str) -> tuple[Image.Image, str] | None:
    """The project's logo and its file name, when the repository has one Pillow can open."""
    owner, name = full_name.split("/")
    with _open(f"https://api.github.com/repos/{full_name}/git/trees/{urllib.parse.quote(branch)}?recursive=1") as response:
        tree = json.load(response)["tree"]
    files = {entry["path"]: entry.get("size", 0) for entry in tree if entry.get("type") == "blob"}
    readmes = sorted((path for path in files if "/" not in path and path.lower().startswith("readme")),
                     key=lambda path: (not path.lower().endswith(".md"), path))
    readme = _raw(full_name, branch, readmes[0]).decode("utf-8", "replace") if readmes else ""
    for path in logo_candidates(files, readme, owner, name)[:MAX_LOGO_TRIES]:
        logo = Image.open(io.BytesIO(_raw(full_name, branch, path)))
        logo.load()
        if logo.width <= 2 * logo.height and logo.height <= 2 * logo.width:
            return logo, posixpath.basename(path)
    return None  # a long logo with its name written out would be cut off in the square


def fetch_repository(text: str) -> dict:
    """Title, description, statistics, languages and picture of a public repository: its logo
    when it has one, else its owner's avatar."""
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
        try:
            logo = _project_logo(repo["full_name"], repo["default_branch"])
        except (urllib.error.URLError, OSError, ValueError, KeyError, Image.DecompressionBombError):
            logo = None  # the owner's picture then
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
        "image": picture,
        "image_name": picture_name,  # the logo's file name; empty for the owner's picture
    }
