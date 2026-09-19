<p align="center">
  <img src="src/vetrina/assets/logo/vetrina-1024.png" width="112" alt="Vetrina logo">
</p>

<h1 align="center">Vetrina</h1>

<p align="center">
  Social preview images for your GitHub repositories, made in seconds on your desktop.
</p>

<p align="center">
  <a href="https://github.com/matteodisalvo/vetrina/releases/latest"><img src="https://img.shields.io/github/v/release/matteodisalvo/vetrina?label=download" alt="Latest release"></a>
  <a href="https://github.com/matteodisalvo/vetrina/actions/workflows/tests.yml"><img src="https://github.com/matteodisalvo/vetrina/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <img src="https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white" alt="macOS">
  <img src="https://img.shields.io/badge/Windows-0078D4?logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHRpdGxlPldpbmRvd3M8L3RpdGxlPjxwYXRoIGZpbGw9IndoaXRlIiBkPSJNMCAwaDExLjM3N3YxMS4zNzJIMHptMTIuNjIzIDBIMjR2MTEuMzcySDEyLjYyM3pNMCAxMi42MjNoMTEuMzc3VjI0SDB6bTEyLjYyMyAwSDI0VjI0SDEyLjYyM3oiLz48L3N2Zz4K" alt="Windows">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license"></a>
</p>

<p align="center"><a href="README.it.md">Leggi in italiano</a></p>

<p align="center">
  <img src="docs/images/poster.png" alt="Vetrina: turn any GitHub repository into a beautiful social preview">
</p>

## 🎬 How it works

<p align="center">
  <img src="docs/images/demo.gif" alt="Vetrina loading a repository, then switching theme, format and bar color">
</p>

## ⬇️ Download

<p align="center">
  <a href="https://github.com/matteodisalvo/vetrina/releases/latest"><img src="https://img.shields.io/badge/Download_for_macOS-000000?style=for-the-badge&logo=apple&logoColor=white" alt="Download for macOS"></a>
  <a href="https://github.com/matteodisalvo/vetrina/releases/latest"><img src="https://img.shields.io/badge/Download_for_Windows-0078D4?style=for-the-badge&logo=data:image/svg%2bxml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHRpdGxlPldpbmRvd3M8L3RpdGxlPjxwYXRoIGZpbGw9IndoaXRlIiBkPSJNMCAwaDExLjM3N3YxMS4zNzJIMHptMTIuNjIzIDBIMjR2MTEuMzcySDEyLjYyM3pNMCAxMi42MjNoMTEuMzc3VjI0SDB6bTEyLjYyMyAwSDI0VjI0SDEyLjYyM3oiLz48L3N2Zz4K" alt="Download for Windows"></a>
</p>

Free and open source, no account needed. The first time you open it, follow the
[install steps](#-install) below.

## ✨ Features

Paste the link of a public repository and Vetrina fills in the card for you: title,
description, contributors, issues, stars, forks, the colors of its languages and the
project's logo (or, when it has none, the owner's avatar). Change anything you like,
watch the preview follow along, and save a PNG.

- **Every social network's size**: GitHub (1280 × 640), LinkedIn (1200 × 627),
  Open Graph (1200 × 630) and X (1200 × 675).
- **Light or dark cards**, with the bottom bar in the colors of the repository's
  languages or in one color of your choice.
- **Your own picture**, chosen from a file or dropped on the window.
- **Preview at full size** before saving; the PNG is drawn at twice its size and scaled
  down, for smooth edges.
- **Speaks five languages**: English, Italian, Spanish, French and German, in light or dark mode.

## 🖼️ Example

A card made with Vetrina for one of my projects:

<p align="center">
  <img src="docs/images/example-card.png" width="640" alt="A card made with Vetrina">
</p>

## 📦 Install

Download the file for your system from the
[latest release](https://github.com/matteodisalvo/vetrina/releases/latest).

### <img src="docs/images/apple.svg" height="20" alt=""> macOS

1. Download `Vetrina-<version>-macOS.dmg` and open it.
2. Drag **Vetrina** onto **Applications**.
3. The first time, macOS may say it cannot check the developer, because the app is not
   notarized by Apple. Open **System Settings → Privacy & Security**, scroll down and
   click **Open Anyway**. You only need to do this once.

The disk image is built for Apple silicon (M1 and later). On an Intel Mac,
[run Vetrina from source](#run-from-source).

### <img src="docs/images/windows.svg" height="18" alt=""> Windows

1. Download `Vetrina-<version>-Windows.exe`.
2. Double-click it: there is nothing to install.
3. If Windows SmartScreen warns about an unknown publisher, click **More info → Run anyway**.

### Run from source

On any system with Python 3.10 or newer and Tk:

```bash
git clone https://github.com/matteodisalvo/vetrina.git
cd vetrina
python3 -m pip install .
vetrina                 # or: python3 -m vetrina
```

## 🚀 How to use it

1. Paste `owner/repository`, or the link of a repository, at the top and press **Load from GitHub**.
2. Edit the title, the description, the picture or the statistics; the preview follows each change.
3. Pick the format and the theme above the preview, then click **Save PNG…** (⌘S on macOS, Ctrl+S on Windows).

To make the card your repository's preview on GitHub, open the repository's
**Settings → General → Social preview → Edit → Upload an image**.

### GitHub's limit

Without an account, GitHub answers 60 requests an hour from each connection. Vetrina uses 3
for each repository, about 20 loads an hour, and a repository loaded again within the hour
costs nothing. To lift the limit to 5,000 requests an hour, paste a GitHub token in the
**Info** window ([create one](https://github.com/settings/personal-access-tokens/new): the
default, read-only access to public repositories, is enough). If the
[GitHub CLI](https://cli.github.com) is installed and signed in, Vetrina uses its token on
its own. The token stays on your computer and is sent only to GitHub.

## 💡 How it started

Vetrina was born out of a need, like all good things (and quite a few bad ones).

Every time I finished a project I would proudly add it to my LinkedIn profile. Link
pasted, description polished, post… and where the preview should have been, nothing.
No thumbnail. The project was there, but it had shown up to the job interview in pajamas.

At least in my case, the thumbnail did not make itself, LinkedIn had no intention of
making one up, and I had no wish to open a graphics program every time to line up the
title, the stars and the counters to the pixel.

So I did what every programmer does when facing a boring five-minute task: I spent
several evenings writing a program to do it for me. And since it was there anyway, I
thought I would share it. If your projects also leave the house in pajamas, Vetrina is
here to dress them.

## 🛠️ Development

```bash
python3 -m pip install -e ".[dev]"   # the app, pytest and ruff
pytest                               # run the tests
ruff check src tests                 # check the style
```

```
vetrina/
├── src/vetrina/
│   ├── model.py         # the card: formats, themes, labels, language colors
│   ├── rendering.py     # draws the card with Pillow
│   ├── github.py        # reads a repository from the GitHub API
│   ├── i18n.py          # every text of the window, in every language
│   ├── settings.py      # remembers the language and the appearance
│   ├── paths.py         # where the bundled assets are
│   ├── assets/          # logo and icon font
│   └── ui/
│       ├── app.py       # the main window
│       ├── widgets.py   # glass buttons, segmented choices, fields, drop zone
│       ├── theme.py     # colors of the window, light and dark
│       ├── icons.py     # line icons from an icon font
│       └── imaging.py   # picture helpers for the window
├── tests/               # pytest suite
├── packaging/           # PyInstaller recipe, build scripts and app icons
└── .github/workflows/   # tests on every push, apps on every release
```

The drawing, the GitHub client and the translations do not depend on the window, so
they can be tested without a display.

### Build the apps

```bash
python3 -m pip install -e ".[build]"   # adds PyInstaller
bash packaging/build-macos.sh          # on a Mac: dist/Vetrina-<version>-macOS.dmg
```

On Windows, run `packaging\build-windows.ps1` in PowerShell to get
`dist\Vetrina-<version>-Windows.exe`. PyInstaller builds for the system it runs on, so
each app is built on its own system.

### Publish a release

The apps to download are not kept in the repository: GitHub builds them and attaches
them to a release, on the repository's **Releases** page. To publish a new version:

1. Write the new version number in `pyproject.toml` and in `src/vetrina/__init__.py`
   (the file names of the apps come from here) and note what changed in `CHANGELOG.md`.
2. Commit, then push a tag with the same number preceded by `v`:

```bash
git tag v<version>
git push origin v<version>
```

GitHub builds the macOS and the Windows app and creates the release with both files
attached. From the **Actions** tab you can also run the **Release** workflow by hand: it
builds the apps as a test, without publishing anything.

## 🌍 Translations

All the texts live in [`src/vetrina/i18n.py`](src/vetrina/i18n.py), each one with its
five languages side by side. To add a language, add its code to `LANGUAGES` and a text to
every entry; the tests check that no text is missing and that every translation fills in
the same values. Corrections from native speakers are very welcome.

## 🙏 Credits

- Icons from [Tabler Icons](https://tabler.io/icons), MIT license
  (see [its license](src/vetrina/assets/fonts/LICENSE-tabler-icons.txt)).
- Built with [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter),
  [Pillow](https://python-pillow.org) and [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2).
- Repository data from the [GitHub REST API](https://docs.github.com/en/rest).

## 📄 License

[MIT](LICENSE) © 2026 Matteo Di Salvo

Made by **Matteo Di Salvo**: [GitHub](https://github.com/matteodisalvo) ·
[website](https://matteodisalvo.github.io/)

## ☕ Buy me a coffee

If Vetrina saved you from a few empty previews and you would like to say thanks, you can
buy me a coffee:

<p align="center">
  <a href="https://buymeacoffee.com/matteodisalvo"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" height="50" alt="Buy Me a Coffee"></a>
</p>
