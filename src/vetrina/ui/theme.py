"""Colors and styles of the window.

Every color is a (light, dark) pair: the window takes the appearance chosen with its button,
or the system's.
"""

from __future__ import annotations

import sys

BACKGROUND = ("#f4f6fa", "#0f1115")
SURFACE = ("#ffffff", "#181b21")
BORDER = ("#e6e9ef", "#262a32")
FIELD = ("#ffffff", "#12151a")
FIELD_BORDER = ("#dde1e8", "#343a44")
DROP = ("#f8f9fb", "#14171c")
DASH = ("#c9d0da", "#3d444f")
TRACK = ("#f1f3f7", "#22262d")
TRACK_HOVER = ("#e6e9ef", "#2b3038")
RAISED = ("#ffffff", "#353b45")
STAGE = ("#f1f3f6", "#0c0e11")
CARD_EDGE = ("#e4e7ec", "#2a2f37")  # a hairline around the preview, for dark cards on the dark stage
TEXT = ("#1f2328", "#e6e8eb")
SUBTLE = ("#4b5563", "#b4bac4")
MUTED = ("#6b7280", "#8d949e")
WHITE = ("#ffffff", "#ffffff")
ACCENT = ("#2563eb", "#3b82f6")
ACCENT_SOFT = ("#e8f0fe", "#1b2a47")
ACCENT_TEXT = ("#1d5fd6", "#8ab4ff")
ERROR = ("#cf222e", "#f85149")
STATUS_COLORS = {"info": MUTED, "error": ERROR, "ok": ("#1a7f37", "#3fb950")}

#: Glass buttons: the two ends of the body gradient, the hairline around it, the light
#: along its upper edge and the glow along its lower edge, the label, and how dark the
#: shadow is; each as (light, dark).
GLASS_STYLES = {
    "glass": {"top": ("#ffffff", "#353b45"), "bottom": ("#f0f2f5", "#272b33"), "rim": ("#dde1e8", "#474e5a"),
              "shine": ("#ffffff", "#5d6572"), "glow": ("#ffffff", "#343a44"), "text": TEXT, "shadow": (0.9, 2.0)},
    "accent": {"top": ("#4d8df8", "#5b97fa"), "bottom": ("#2563eb", "#2e6be6"), "rim": ("#2158d6", "#3b78ee"),
               "shine": ("#9fc0fc", "#a6c5fd"), "glow": ("#3f7cf2", "#4a84f3"), "text": WHITE, "shadow": (1.6, 2.2)},
}

#: Mouse pointer over things to click, and the modifier key of the keyboard shortcuts.
POINTER = "pointinghand" if sys.platform == "darwin" else "hand2"
MODIFIER = "Command" if sys.platform == "darwin" else "Control"


def mix(first: str, second: str, amount: float) -> str:
    """The color ``amount`` of the way from ``first`` to ``second`` (both "#rrggbb")."""
    a, b = (tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)) for color in (first, second))
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b, strict=True))
