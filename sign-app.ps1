param(
    [string]$Subject = "CN=DeTrace Self-Signed Code Signing",
    [string[]]$Paths = @("dist\DeTrace.exe", "installer\DeTraceSetup.exe"),
    [switch]$SkipTrust
)

$ErrorActionPreference = "Stop"

function Resolve-SignPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    $resolved = Join-Path $PSScriptRoot $Path
    if (-not (Test-Path -LiteralPath $resolved)) {
        throw "File was not found: $resolved"
    }
    return (Resolve-Path -LiteralPath $resolved).Path
}

function Get-DeTraceCertificate {
    param([Parameter(Mandatory = $true)][string]$Subject)

    $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Subject -eq $Subject -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1

    if ($cert) {
        return $cert
    }

    return New-SelfSignedCertificate `
        -Type CodeSigningCert `
        -Subject $Subject `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -KeyAlgorithm RSA `
        -KeyLength 3072 `
        -HashAlgorithm SHA256 `
        -NotAfter (Get-Date).AddYears(5)
}

function Trust-CertificateForCurrentUser {
    param([Parameter(Mandatory = $true)]$Certificate)

    $rootPath = "Cert:\CurrentUser\Root\$($Certificate.Thumbprint)"
    if (Test-Path -LiteralPath $rootPath) {
        return
    }

    $exportPath = Join-Path $env:TEMP "DeTrace-CodeSigning-$($Certificate.Thumbprint).cer"
    Export-Certificate -Cert $Certificate -FilePath $exportPath | Out-Null
    Import-Certificate -FilePath $exportPath -CertStoreLocation Cert:\CurrentUser\Root | Out-Null
    Remove-Item -LiteralPath $exportPath -Force
}

$cert = Get-DeTraceCertificate -Subject $Subject
if (-not $SkipTrust) {
    Trust-CertificateForCurrentUser -Certificate $cert
}

foreach ($path in $Paths) {
    $resolved = Resolve-SignPath -Path $path
    $signature = Set-AuthenticodeSignature -FilePath $resolved -Certificate $cert -HashAlgorithm SHA256
    if ($signature.Status -ne "Valid" -and -not $SkipTrust) {
        throw "Signing failed for $resolved. Status: $($signature.Status). $($signature.StatusMessage)"
    }
    if ($signature.Status -ne "Valid") {
        Write-Warning "Signed, but Windows does not fully trust the certificate yet. Status: $($signature.Status). $($signature.StatusMessage)"
    }
    Write-Host "Signed: $resolved"
}

Write-Host "Certificate: $($cert.Subject)"
Write-Host "Thumbprint: $($cert.Thumbprint)"
