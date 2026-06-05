$ErrorActionPreference = "Stop"

function Find-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return "python"
    }

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return "py -3"
    }

    return $null
}

function Install-Python {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Python is not installed and winget is not available. Install Python 3.11+ from https://www.python.org/downloads/ and run this script again."
    }

    Write-Host "Python was not found. Installing Python 3 with winget..."
    winget install --id Python.Python.3.11 --source winget --accept-package-agreements --accept-source-agreements

    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

$python = Find-Python
if (-not $python) {
    Install-Python
    $python = Find-Python
}

if (-not $python) {
    throw "Python installation finished, but Python is still not available on PATH. Open a new terminal and run setup-and-run.ps1 again."
}

Write-Host "Using Python: $python"
Invoke-Expression "$python -m pip install --upgrade pip"
Invoke-Expression "$python -m pip install -r requirements.txt"
Invoke-Expression "$python server.py"
