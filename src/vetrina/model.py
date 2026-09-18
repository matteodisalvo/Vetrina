"""The card: what ends up on a thumbnail, and the sizes, themes and labels it can take."""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image

#: Output formats: name shown in the window -> size in pixels.
PRESETS = {
    "GitHub": (1280, 640),
    "LinkedIn": (1200, 627),
    "Open Graph": (1200, 630),
    "X / Twitter": (1200, 675),
}

#: Colors of each theme.
THEMES = {
    "Chiaro": {"background": "#ffffff", "title": "#1f2328", "text": "#59636e"},
    "Scuro": {"background": "#0d1117", "title": "#f0f6fc", "text": "#9198a1"},
}

#: Statistic labels: contributor (singular), contributors (plural), issues, stars, forks.
LABELS = {
    "English": ("Contributor", "Contributors", "Issues", "Stars", "Forks"),
    "Italiano": ("Collaboratore", "Collaboratori", "Issue", "Stelle", "Fork"),
}

#: Colors GitHub uses for common languages; any other language is drawn in gray.
LANGUAGE_COLORS = {
    "Python": "#3572A5", "Jupyter Notebook": "#DA5B0B", "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6", "HTML": "#e34c26", "CSS": "#663399", "SCSS": "#c6538c",
    "C": "#555555", "C++": "#f34b7d", "C#": "#178600", "Java": "#b07219",
    "Kotlin": "#A97BFF", "Swift": "#F05138", "Objective-C": "#438eff", "Go": "#00ADD8",
    "Rust": "#dea584", "Ruby": "#701516", "PHP": "#4F5D95", "R": "#198CE7",
    "MATLAB": "#e16737", "Julia": "#a270ba", "Shell": "#89e051", "PowerShell": "#012456",
    "Dockerfile": "#384d54", "Makefile": "#427819", "CMake": "#DA3434", "TeX": "#3D6117",
    "Fortran": "#4d41b1", "Dart": "#00B4AB", "Vue": "#41b883", "Lua": "#000080",
    "Haskell": "#5e5086", "Scala": "#c22d40", "Perl": "#0298c3", "Cython": "#fedf5b",
    "Assembly": "#6E4C13", "Verilog": "#b2b7f8", "VHDL": "#adb2cb",
}
OTHER_LANGUAGE_COLOR = "#8b949e"


@dataclass
class Card:
    """Everything that ends up on the thumbnail."""

    title: str = "owner/repository"
    description: str = "A short description of the project."
    image: Image.Image | None = None
    show_stats: bool = True
    stats: tuple[int, int, int, int] = (1, 0, 0, 0)  # contributors, issues, stars, forks
    languages: dict[str, int] = field(default_factory=dict)
    use_language_colors: bool = True
    accent: str = "#3572A5"
    theme: str = "Chiaro"
    size: tuple[int, int] = (1280, 640)
    labels: str = "English"
    footer: str = ""
