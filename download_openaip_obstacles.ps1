# Ref: https://cloud.google.com/storage/docs/requester-pays
# Ref: https://cloud.google.com/storage/docs/json_api/v1/objects/get
# Ref: https://learn.microsoft.com/powershell/module/microsoft.powershell.core/about/about_functions_advanced_parameters
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, HelpMessage = "Requester's Google Cloud project ID.")]
    [string]$GoogleCloudProject
)

$ErrorActionPreference = 'Stop'

# Ref: https://cloud.google.com/sdk/docs/install
# Ref: https://cloud.google.com/sdk/docs/downloads-interactive#silent
function Resolve-Gcloud {
    # Already on PATH?
    $cmd = Get-Command gcloud -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }

    # Common install location (per-user default for the interactive installer)
    $default = Join-Path $env:LOCALAPPDATA "Google\Cloud SDK\google-cloud-sdk\bin"
    if (Test-Path (Join-Path $default "gcloud.cmd")) {
        $env:Path = "$default;$env:Path"
        return (Join-Path $default "gcloud.cmd")
    }
    return $null
}

if (-not (Resolve-Gcloud)) {
    Write-Host "gcloud not found. Downloading Google Cloud SDK installer..."

    $installerUrl = "https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe"
    $installer    = Join-Path $env:TEMP "GoogleCloudSDKInstaller.exe"

    Invoke-WebRequest -Uri $installerUrl -OutFile $installer

    Write-Host "Installing (this may take a few minutes)..."
    # /S = silent install
    $proc = Start-Process -FilePath $installer -ArgumentList "/S" -Wait -PassThru
    if ($proc.ExitCode -ne 0) {
        throw "Cloud SDK installer exited with code $($proc.ExitCode)."
    }

    if (-not (Resolve-Gcloud)) {
        throw "gcloud still not found after install. Open a NEW shell, run 'gcloud init', then re-run this script."
    }
    Write-Host "Cloud SDK installed."
}

# https://www.openaip.net/docs "Scheduled Data Exports" section.
$Bucket    = "29f98e10-a489-4c82-ae5e-489dbcd4912f"
$OutDir    = Join-Path $PWD "raw/openaip_obstacles"
$Suffix    = "_obs.json"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Short-lived (~1h) access token from an existing gcloud login / service account
$Token   = (& gcloud auth print-access-token).Trim()
$Headers = @{ Authorization = "Bearer $Token" }

# Ref: https://cloud.google.com/storage/docs/json_api/v1/objects/list
# List + download in one pass. items(name,generation,updated) gives us the
# "if-modified-since" marker directly, so no separate metadata GET is needed.
Write-Host @"
This program uses local last updated time to compare file versions between local and remote. 
If any file in $OutDir was written again locally, please delete them and run this program again.
"@
$pageToken = $null
do {
    $listUrl = "https://storage.googleapis.com/storage/v1/b/$Bucket/o" +
               "?fields=items(name,generation,updated),nextPageToken&userProject=$GoogleCloudProject"
    if ($pageToken) { $listUrl += "&pageToken=$pageToken" }

    $page = Invoke-RestMethod -Uri $listUrl -Headers $Headers -Method Get

    foreach ($item in $page.items) {
        if ($item.name -notlike "*$Suffix") { continue }

        $obj      = $item.name
        $objEnc   = [uri]::EscapeDataString($obj)
        $mediaUrl = "https://storage.googleapis.com/storage/v1/b/$Bucket/o/$objEnc" +
                    "?alt=media&userProject=$GoogleCloudProject"

        $outFile   = Join-Path $OutDir $obj

        try {
            # Parse remote 'updated' (RFC 3339) as UTC
            $remoteUpdated = ([datetimeoffset]$item.updated).UtcDateTime

            $needsDownload = $true
            if (Test-Path $outFile) {
                $localUpdated = (Get-Item $outFile).LastWriteTimeUtc
                # Remote not newer than local  ->  skip. 1s tolerance for fs granularity.
                if ($remoteUpdated -le $localUpdated.AddSeconds(1)) { $needsDownload = $false }
            }

            if ($needsDownload) {
                New-Item -ItemType Directory -Force -Path (Split-Path $outFile) | Out-Null
                Invoke-WebRequest -Uri $mediaUrl -Headers $Headers -OutFile $outFile
                # Stamp the local file's mtime to match the remote 'updated' time
                (Get-Item $outFile).LastWriteTimeUtc = $remoteUpdated
                Write-Host "[UPDATED] $obj  ($($item.updated))"
            }
            else {
                Write-Host "[SKIP]    $obj  (unchanged)"
            }
        }
        catch {
            Write-Warning "[ERROR]   $obj  -> $($_.Exception.Message)"
        }
    }

    $pageToken = $page.nextPageToken
} while ($pageToken)
