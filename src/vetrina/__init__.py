"""Vetrina: social preview images for GitHub repositories.

A desktop app that loads a public repository from GitHub (title, description, statistics,
languages and logo, or owner avatar), lets every detail be edited with a live preview, and
saves the card as a PNG in the sizes GitHub, LinkedIn, Open Graph and X expect.
"""

__version__ = "1.2.0"

APP_NAME = "Vetrina"

#: The repository of the app, where people can leave a star.
REPOSITORY = "https://github.com/matteodisalvo/Vetrina"

#: Who made the app and where to follow them, for the info window: (name in i18n.TEXTS
#: or shown as it is, icon, address).
AUTHOR = "Matteo Di Salvo"
LINKS = [
    ("GitHub", "brand-github", "https://github.com/matteodisalvo"),
    ("website", "world-www", "https://matteodisalvo.github.io/"),
]
