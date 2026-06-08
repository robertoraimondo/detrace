$ErrorActionPreference = "Stop"

function Remove-IfExists {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python is required to build DeTrace.exe. Run setup-and-run.ps1 first or install Python 3.11+."
}

Remove-IfExists "build"
Remove-IfExists "dist"
Remove-IfExists "__pycache__"

python -m pip install --upgrade pip
python -m pip install pyinstaller
Remove-IfExists "wheelhouse"
python -m pip wheel -r requirements.txt --wheel-dir wheelhouse

python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name DeTrace `
    --icon "assets\detrace-icon.ico" `
    --runtime-tmpdir ".detrace-pyi" `
    --add-data "requirements.txt;." `
    --add-data "server.py;." `
    --add-data "desktop_window.py;." `
    --add-data "static;static" `
    --add-data "wheelhouse;wheelhouse" `
    --add-data "models;models" `
    detrace_launcher.py

Remove-IfExists "dist\.detrace-app"
Remove-IfExists "dist\.detrace-runtime"
Remove-IfExists "dist\.detrace-pyi"
Remove-IfExists "dist\workspace"
Remove-IfExists "dist\__pycache__"
New-Item -ItemType Directory -Path "dist\.detrace-pyi" | Out-Null

& (Join-Path $PSScriptRoot "sign-app.ps1") -Paths @("dist\DeTrace.exe") -SkipTrust

Write-Host "Built executable: dist\DeTrace.exe"
