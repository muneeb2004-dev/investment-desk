# PowerShell translation of setup_cloud_scheduler.sh, for Windows hosts
# without a bash shell.
#
# Creates (or updates) the Cloud Scheduler job that fires the 8am daily
# report. Reads BACKEND_API_KEY straight out of backend/.env so the key
# is never typed on a command line or left in shell history.
#
# REQUIRES BILLING ENABLED on the project — Cloud Scheduler cannot be
# activated on a project without an open billing account.
#
# Usage:
#   .\scripts\setup_cloud_scheduler.ps1 `
#       -BackendUrl "https://xxxx.trycloudflare.com" `
#       -GcpProject "your-gcp-project-id" `
#       -UserId "muneeb"
#
# NOTE: quick tunnels (cloudflared / ngrok free tier) get a NEW url every
# time you restart them. If you restart the tunnel, re-run this script
# with the new URL before recording the demo, or the job will 404.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $BackendUrl,
    [Parameter(Mandatory = $true)] [string] $GcpProject,
    [string] $UserId   = "muneeb",
    [string] $TimeZone = "America/Los_Angeles",
    [string] $JobName  = "investment-desk-daily-report"
)

$ErrorActionPreference = "Stop"

# gcloud is a .cmd shim and is often not on PATH in the shell that
# installed it; fall back to the known install locations.
$gcloud = (Get-Command gcloud -ErrorAction SilentlyContinue).Source
if (-not $gcloud) {
    $gcloud = @(
        "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
        "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $gcloud) { throw "gcloud not found. Install the Google Cloud SDK first." }

# Pull the shared secret from backend/.env rather than taking it as a
# parameter, so it stays out of the command line and shell history.
$envPath = Join-Path $PSScriptRoot "..\backend\.env"
if (-not (Test-Path $envPath)) { throw "backend/.env not found at $envPath" }
$match = Select-String -Path $envPath -Pattern '^BACKEND_API_KEY=(.*)$'
if (-not $match) { throw "BACKEND_API_KEY not set in backend/.env" }
$BackendApiKey = $match.Matches.Groups[1].Value.Trim()
if ([string]::IsNullOrWhiteSpace($BackendApiKey)) { throw "BACKEND_API_KEY is empty in backend/.env" }

$BackendUrl = $BackendUrl.TrimEnd('/')

Write-Host "Project : $GcpProject"
Write-Host "Target  : $BackendUrl/daily-report"
Write-Host "User    : $UserId"
Write-Host "Schedule: 0 8 * * *  ($TimeZone)"
Write-Host ""

& $gcloud config set project $GcpProject
& $gcloud services enable cloudscheduler.googleapis.com --project $GcpProject

# --headers takes a single comma-separated string; the API key is
# interpolated here but never echoed.
$headers = "Content-Type=application/json,X-Backend-Api-Key=$BackendApiKey"
$body    = "{`"user_id`": `"$UserId`"}"

$common = @(
    "--schedule=0 8 * * *"
    "--time-zone=$TimeZone"
    "--uri=$BackendUrl/daily-report"
    "--http-method=POST"
    "--headers=$headers"
    "--message-body=$body"
    "--project=$GcpProject"
)

Write-Host "Creating job '$JobName' ..."
& $gcloud scheduler jobs create http $JobName @common `
    "--description=Investment Desk - personalized 8am daily report (Reporting Agent trigger)"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Create failed (job likely already exists) - updating instead ..."
    & $gcloud scheduler jobs update http $JobName @common
    if ($LASTEXITCODE -ne 0) { throw "Both create and update failed for job '$JobName'." }
}

Write-Host ""
Write-Host "Done. Verify with:"
Write-Host "  gcloud scheduler jobs list --project=$GcpProject"
Write-Host ""
Write-Host "Trigger it once right now to prove it works, without waiting for 8am:"
Write-Host "  gcloud scheduler jobs run $JobName --project=$GcpProject"
