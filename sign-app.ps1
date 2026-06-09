param(
    [string]$Subject = "CN=DeTrace Self-Signed Code Signing",
    [string[]]$Paths = @("dist\DeTrace.exe", "installer\DeTraceSetup.exe"),
    [string]$CertificateThumbprint = $env:DETRACE_SIGN_CERT_THUMBPRINT,
    [string]$PfxPath = $env:DETRACE_SIGN_CERT_PFX,
    [string]$PfxPassword = $env:DETRACE_SIGN_CERT_PASSWORD,
    [string]$ExportCertificatePath,
    [switch]$SkipTrust,
    [switch]$NoCreate
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
    param(
        [Parameter(Mandatory = $true)][string]$Subject,
        [string]$CertificateThumbprint,
        [string]$PfxPath,
        [string]$PfxPassword,
        [switch]$NoCreate
    )

    if ($CertificateThumbprint) {
        $normalizedThumbprint = $CertificateThumbprint.Replace(" ", "")
        $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
            Where-Object { $_.Thumbprint -eq $normalizedThumbprint -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
            Select-Object -First 1

        if ($cert) {
            return $cert
        }
    }

    if ($PfxPath) {
        $resolvedPfxPath = Join-Path $PSScriptRoot $PfxPath
        if (-not (Test-Path -LiteralPath $resolvedPfxPath)) {
            $resolvedPfxPath = $PfxPath
        }
        if (-not (Test-Path -LiteralPath $resolvedPfxPath)) {
            throw "Signing PFX was not found: $PfxPath"
        }

        $securePassword = if ($PfxPassword) {
            ConvertTo-SecureString -String $PfxPassword -AsPlainText -Force
        } else {
            Read-Host "PFX password" -AsSecureString
        }

        $imported = Import-PfxCertificate `
            -FilePath $resolvedPfxPath `
            -CertStoreLocation Cert:\CurrentUser\My `
            -Password $securePassword

        $cert = $imported | Where-Object { $_.HasPrivateKey } | Select-Object -First 1
        if ($cert) {
            return $cert
        }
    }

    $cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert |
        Where-Object { $_.Subject -eq $Subject -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1

    if ($cert) {
        return $cert
    }

    if ($NoCreate) {
        throw "No reusable DeTrace signing certificate was found. Import a PFX with DETRACE_SIGN_CERT_PFX or set DETRACE_SIGN_CERT_THUMBPRINT."
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

$cert = Get-DeTraceCertificate `
    -Subject $Subject `
    -CertificateThumbprint $CertificateThumbprint `
    -PfxPath $PfxPath `
    -PfxPassword $PfxPassword `
    -NoCreate:$NoCreate
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

if ($ExportCertificatePath) {
    $resolvedExportPath = Join-Path $PSScriptRoot $ExportCertificatePath
    $exportDirectory = Split-Path -Parent $resolvedExportPath
    if ($exportDirectory) {
        New-Item -ItemType Directory -Path $exportDirectory -Force | Out-Null
    }
    Export-Certificate -Cert $cert -FilePath $resolvedExportPath | Out-Null
    Write-Host "Exported public certificate: $resolvedExportPath"
}

Write-Host "Certificate: $($cert.Subject)"
Write-Host "Thumbprint: $($cert.Thumbprint)"
