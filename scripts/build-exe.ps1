# Builds the distributable: dist\Alembic-<version>.zip containing an
# Alembic\ folder with SkyrimAlchemyEffectFinder.exe and its libraries.
#
# Uses PyInstaller --onedir (NOT --onefile): a single self-extracting exe
# is the classic antivirus-heuristic trigger, because unpacking yourself
# at launch is also how malware droppers behave. A plain folder of exe +
# DLLs is the same app with far fewer false positives.
#
# Builds from a throwaway venv holding only the runtime deps, so the
# result doesn't inherit whatever else the dev environment has installed.
#
# Usage (from the repo root):  powershell -File scripts\build-exe.ps1

$ErrorActionPreference = "Stop"

$version = python -c "import alchemy_helper; print(alchemy_helper.__version__)"

$venv = Join-Path $env:TEMP "alchemy-helper-buildenv"
python -m venv $venv
& "$venv\Scripts\python" -m pip install --quiet . pyinstaller

& "$venv\Scripts\python" -m PyInstaller --noconfirm --onedir `
    --name SkyrimAlchemyEffectFinder `
    --paths . `
    --add-data "alchemy_helper/web/static;alchemy_helper/web/static" `
    --add-data "alchemy_helper/data/effects.json;alchemy_helper/data" `
    --add-data "alchemy_helper/data/ingredients.json;alchemy_helper/data" `
    alchemy_helper/__main__.py

# Zip with a friendly top-level folder name
$staging = "dist\Alembic"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
Copy-Item -Recurse "dist\SkyrimAlchemyEffectFinder" $staging
$zip = "dist\Alembic-$version.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $staging -DestinationPath $zip

Write-Host "Built $zip (folder build, v$version)"
