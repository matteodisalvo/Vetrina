"""Line icons drawn as characters of an icon font: text is what Tk draws at full Retina
resolution with smooth edges (its lines and polygons snap to whole points), and a
character takes any color.

assets/fonts/tabler-icons.ttf holds only the icons below, cut from the Tabler Icons webfont
3.46.0 (https://tabler.io/icons), MIT License: see assets/fonts/LICENSE-tabler-icons.txt.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
import tkinter as tk
import tkinter.font

from ..paths import ICON_FONT_FILE

FAMILY = "tabler-icons"

#: Icon name -> its character in the font.
ICONS = {
    "link": "\ueade", "download": "\uea96", "letter-t": "\uec63", "photo": "\ueb0a",
    "upload": "\ueb47", "trash": "\ueb41", "chart-bar": "\uea59", "world": "\ueb54",
    "palette": "\ueb01", "brand-github": "\uec1c", "brand-linkedin": "\uec8c", "share": "\ueb21",
    "brand-x": "\ufc0f", "sun": "\ueb30", "moon": "\ueaf8", "eye": "\uea9a",
    "info-circle": "\ueac5", "world-www": "\uf38f", "language": "\uebbe", "chevron-down": "\uea5f",
}

#: Whether the font is available to Tk; set by check().
available = False


def register_font() -> None:
    """Make the icon font usable by this process only. It must happen before the Tk window
    exists, which reads the fonts when it starts: through Core Text on macOS, GDI on Windows."""
    if not ICON_FONT_FILE.exists():
        return
    if sys.platform == "win32":
        try:
            ctypes.windll.gdi32.AddFontResourceExW(str(ICON_FONT_FILE), 0x10, 0)  # 0x10: FR_PRIVATE
        except (AttributeError, OSError):
            pass
        return
    if sys.platform != "darwin":
        return
    try:
        core_foundation = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
        core_text = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreText"))
    except (OSError, TypeError):
        return
    core_foundation.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    core_foundation.CFURLCreateFromFileSystemRepresentation.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool]
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    core_text.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    core_text.CTFontManagerRegisterFontsForURL.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p]
    path = str(ICON_FONT_FILE).encode()
    url = core_foundation.CFURLCreateFromFileSystemRepresentation(None, path, len(path), False)
    if url:
        core_text.CTFontManagerRegisterFontsForURL(url, 1, None)  # 1: for this process only
        core_foundation.CFRelease(url)


def check(root: tk.Misc) -> bool:
    """Record whether Tk can see the icon font; without it the icons are left out."""
    global available
    available = FAMILY in tkinter.font.families(root)
    return available


def font(size: int) -> tuple[str, int]:
    """The icon font at ``size`` points (a negative Tk size is in pixels, which are points on macOS)."""
    return (FAMILY, -size)


def text(name: str) -> str:
    """The character of icon ``name``, or nothing when the font is missing."""
    return ICONS[name] if available else ""
