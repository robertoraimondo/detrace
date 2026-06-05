$ErrorActionPreference = "Stop"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python is required to build DeTrace.exe. Run setup-and-run.ps1 first or install Python 3.11+."
}

python -m pip install --upgrade pip
python -m pip install pyinstaller
if (Test-Path wheelhouse) {
    Remove-Item -Recurse -Force wheelhouse
}
python -m pip wheel -r requirements.txt --wheel-dir wheelhouse

if (-not (Test-Path dist)) {
    New-Item -ItemType Directory -Path dist | Out-Null
}

if (Test-Path dist\DeTrace.exe) {
    Remove-Item -Force dist\DeTrace.exe
}

python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name DeTrace `
    --add-data "requirements.txt;." `
    --add-data "server.py;." `
    --add-data "desktop_window.py;." `
    --add-data "static;static" `
    --add-data "wheelhouse;wheelhouse" `
    detrace_launcher.py

Write-Host "Built executable: dist\DeTrace.exe"
