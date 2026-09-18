"""Where the files that ship with the app are, also inside the packaged .app and .exe."""

from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"

#: The logo: the whole tile for the header and the info window, and the tile on the
#: macOS icon grid (with margin and shadow) for the Dock. Drawn from the SVG files beside them.
LOGO_FILE = ASSETS / "logo" / "vetrina-1024.png"
ICON_FILE = ASSETS / "logo" / "vetrina-icon-512.png"

#: The icon font of the window's buttons.
ICON_FONT_FILE = ASSETS / "fonts" / "tabler-icons.ttf"
