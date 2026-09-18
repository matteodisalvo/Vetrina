#!/usr/bin/env bash
# Builds dist/Vetrina.app and the disk image dist/Vetrina-<version>-macOS.dmg, on a Mac.
# Needs the build tools first: python3 -m pip install -e ".[build]"
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -m PyInstaller packaging/vetrina.spec --noconfirm --clean
version=$(python3 -c "import sys; sys.path.insert(0, 'src'); import vetrina; print(vetrina.__version__)")

# The disk image holds the app and a link to Applications, to drag it onto
staging=$(mktemp -d)
ditto dist/Vetrina.app "$staging/Vetrina.app"
ln -s /Applications "$staging/Applications"
hdiutil create -volname "Vetrina" -srcfolder "$staging" -ov -format UDZO "dist/Vetrina-$version-macOS.dmg"
rm -rf "$staging"
echo "Ready: dist/Vetrina-$version-macOS.dmg"
