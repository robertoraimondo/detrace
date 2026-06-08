$ErrorActionPreference = "Stop"

function Remove-IfExists {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (Test-Path -LiteralPath $Path) {
        Remove-Item -LiteralPath $Path -Recurse -Force
    }
}

$dotnet = Get-Command dotnet.exe -ErrorAction SilentlyContinue
if (-not $dotnet) {
    throw "The .NET SDK is required to build DeTraceSetup.exe and was not found."
}

& (Join-Path $PSScriptRoot "build-exe.ps1")

$exePath = Join-Path $PSScriptRoot "dist\DeTrace.exe"
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "dist\DeTrace.exe was not found. Build the app first with build-exe.ps1."
}

$installerRoot = Join-Path $PSScriptRoot "installer"
$installerSource = Join-Path $PSScriptRoot "installer-src"
$payloadDir = Join-Path $installerSource "payload"
$outputPath = Join-Path $installerRoot "DeTraceSetup.exe"
$publishDir = Join-Path $installerRoot "publish"
$oldDistSetup = Join-Path $PSScriptRoot "dist\DeTraceSetup.exe"

Remove-IfExists $installerRoot
Remove-IfExists $payloadDir
Remove-IfExists $oldDistSetup
Remove-IfExists (Join-Path $PSScriptRoot "dist\~DeTraceSetup.CAB")
Remove-IfExists (Join-Path $PSScriptRoot "dist\~DeTraceSetup.DDF")
Remove-IfExists (Join-Path $PSScriptRoot "dist\~DeTraceSetup.RPT")
Remove-IfExists (Join-Path $PSScriptRoot "dist\~DeTraceSetup_LAYOUT.INF")
New-Item -ItemType Directory -Path $payloadDir | Out-Null
Copy-Item -LiteralPath $exePath -Destination (Join-Path $payloadDir "DeTrace.exe") -Force

Remove-IfExists $outputPath
& $dotnet.Source publish (Join-Path $installerSource "DeTraceSetup.csproj") `
    --configuration Release `
    --runtime win-x64 `
    --self-contained true `
    --output $publishDir `
    -p:PublishSingleFile=true `
    -p:EnableCompressionInSingleFile=true `
    -p:DebugType=None `
    -p:DebugSymbols=false

if ($LASTEXITCODE -ne 0) {
    throw "dotnet publish failed while building DeTraceSetup.exe."
}

$publishedInstaller = Join-Path $publishDir "DeTraceSetup.exe"
if (Test-Path -LiteralPath $publishedInstaller) {
    Copy-Item -LiteralPath $publishedInstaller -Destination $outputPath -Force
}

if (-not (Test-Path -LiteralPath $outputPath)) {
    throw "Installer build did not create installer\DeTraceSetup.exe."
}

Remove-IfExists $publishDir

& (Join-Path $PSScriptRoot "sign-app.ps1") -Paths @("dist\DeTrace.exe", "installer\DeTraceSetup.exe") -SkipTrust

Write-Host "Built installer: installer\DeTraceSetup.exe"
Write-Host "Kept executable: dist\DeTrace.exe"
