# PyInstaller recipe of the desktop apps. From the root of the project:
#     python -m PyInstaller packaging/vetrina.spec --noconfirm
# On macOS it makes dist/Vetrina.app (build-macos.sh then wraps it in a .dmg);
# on Windows, dist/Vetrina.exe, a single file that needs no installation.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT / "src"))
from vetrina import APP_NAME, __version__  # noqa: E402

ICONS = ROOT / "packaging" / "icons"
NATIVE = ["**/*.dylib", "**/*.dll", "**/*.so"]

datas = [(str(ROOT / "src" / "vetrina" / "assets"), "vetrina/assets")]
datas += collect_data_files("customtkinter")  # its themes and fonts
datas += collect_data_files("tkinterdnd2", excludes=NATIVE)  # the Tcl side of drag and drop
binaries = collect_dynamic_libs("tkinterdnd2")  # and its native side

analysis = Analysis(
    [str(ROOT / "src" / "vetrina" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    datas=datas,
    binaries=binaries,
    hiddenimports=["tkinterdnd2"],
    excludes=["pytest", "ruff"],
)
pyz = PYZ(analysis.pure)

if sys.platform == "darwin":
    executable = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name=APP_NAME, console=False,
                     icon=str(ICONS / "vetrina.icns"))
    collected = COLLECT(executable, analysis.binaries, analysis.datas, name=APP_NAME)
    app = BUNDLE(
        collected,
        name=f"{APP_NAME}.app",
        icon=str(ICONS / "vetrina.icns"),
        bundle_identifier="io.github.matteodisalvo.vetrina",
        version=__version__,
        info_plist={
            "CFBundleDisplayName": APP_NAME,
            "CFBundleShortVersionString": __version__,
            "NSHighResolutionCapable": True,
            "LSApplicationCategoryType": "public.app-category.graphics-design",
            "NSHumanReadableCopyright": "© 2026 Matteo Di Salvo. MIT License.",
        },
    )
else:
    executable = EXE(pyz, analysis.scripts, analysis.binaries, analysis.datas, [], name=APP_NAME, console=False,
                     icon=str(ICONS / "vetrina.ico"))
