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

# Always a fresh venv: a reused one can rot (e.g. a Python upgrade or temp
# cleanup breaks its pip) and PowerShell doesn't stop on native-command
# failures - which once produced a stale zip labeled as the new version.
$venv = Join-Path $env:TEMP "alchemy-helper-buildenv"
if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
python -m venv $venv
& "$venv\Scripts\python" -m pip install --quiet . pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install failed (exit $LASTEXITCODE)" }

& "$venv\Scripts\python" -m PyInstaller --noconfirm --onedir `
    --name SkyrimAlchemyEffectFinder `
    --paths . `
    --add-data "alchemy_helper/web/static;alchemy_helper/web/static" `
    --add-data "alchemy_helper/data/effects.json;alchemy_helper/data" `
    --add-data "alchemy_helper/data/ingredients.json;alchemy_helper/data" `
    --add-data "alchemy_helper/data/packs;alchemy_helper/data/packs" `
    alchemy_helper/__main__.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

# Zip with a friendly top-level folder name
$staging = "dist\Alembic"
if (Test-Path $staging) { Remove-Item -Recurse -Force $staging }
Copy-Item -Recurse "dist\SkyrimAlchemyEffectFinder" $staging

# Sanity: the bundle must hold the exe and every dataset pack, or the
# frozen app would run but silently never activate mod support.
if (-not (Test-Path "$staging\SkyrimAlchemyEffectFinder.exe")) {
    throw "bundle check failed: exe missing from $staging"
}
foreach ($pack in Get-ChildItem "alchemy_helper\data\packs\*.json") {
    if (-not (Test-Path "$staging\_internal\alchemy_helper\data\packs\$($pack.Name)")) {
        throw "bundle check failed: pack $($pack.Name) missing from $staging"
    }
}

$zip = "dist\Alembic-$version.zip"
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path $staging -DestinationPath $zip

Write-Host "Built $zip (folder build, v$version)"
