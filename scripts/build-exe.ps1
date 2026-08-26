# Builds dist\SkyrimAlchemyEffectFinder.exe — a standalone, no-Python-needed
# build of the app for end users (Nexus Mods / GitHub Releases).
#
# Builds from a throwaway venv holding only the runtime deps, so the exe
# doesn't inherit whatever else the dev environment has installed (the same
# build from a full dev environment came out 118 MB; from the clean venv,
# ~15 MB).
#
# Usage (from the repo root):  powershell -File scripts\build-exe.ps1

$ErrorActionPreference = "Stop"

$venv = Join-Path $env:TEMP "alchemy-helper-buildenv"
python -m venv $venv
& "$venv\Scripts\python" -m pip install --quiet . pyinstaller

& "$venv\Scripts\python" -m PyInstaller --noconfirm --onefile `
    --name SkyrimAlchemyEffectFinder `
    --paths . `
    --add-data "alchemy_helper/web/static;alchemy_helper/web/static" `
    --add-data "alchemy_helper/data/effects.json;alchemy_helper/data" `
    --add-data "alchemy_helper/data/ingredients.json;alchemy_helper/data" `
    alchemy_helper/__main__.py

Write-Host "Built dist\SkyrimAlchemyEffectFinder.exe"
