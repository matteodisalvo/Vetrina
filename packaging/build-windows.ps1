# Builds dist\Vetrina-<version>-Windows.exe, a single file that needs no installation, on Windows.
# Needs the build tools first: python -m pip install -e ".[build]"
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -m PyInstaller packaging/vetrina.spec --noconfirm --clean
$version = python -c "import sys; sys.path.insert(0, 'src'); import vetrina; print(vetrina.__version__)"
Move-Item -Force dist\Vetrina.exe "dist\Vetrina-$version-Windows.exe"
Write-Host "Ready: dist\Vetrina-$version-Windows.exe"
