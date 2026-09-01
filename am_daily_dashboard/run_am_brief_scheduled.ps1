# AM Brief morning send — Sun-Thu 10:00 AM Israel (separate from daily summary Pages).
param(
    [switch]$EnableAmBriefSlack
)

$ErrorActionPreference = 'Continue'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $ProjectRoot 'am_daily_dashboard\logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogFile = Join-Path $LogDir ("am_brief_{0:yyyy-MM-dd_HHmmss}.log" -f (Get-Date))

function Write-Log([string]$Message) {
    $line = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "Starting AM Brief scheduled run (cwd=$ProjectRoot)"

if (-not $env:GOOGLE_APPLICATION_CREDENTIALS) {
    $DefaultKey = 'c:\Users\Owner\Downloads\key.json.json'
    if (Test-Path $DefaultKey) {
        $env:GOOGLE_APPLICATION_CREDENTIALS = $DefaultKey
        Write-Log "Set GOOGLE_APPLICATION_CREDENTIALS=$DefaultKey"
    }
}

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    $Python = (Get-Command python3 -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    Write-Log "ERROR: Python not found on PATH"
    exit 1
}

Set-Location $ProjectRoot
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$CatchUp = Join-Path $ProjectRoot 'am_daily_dashboard\generate_am_brief_range.py'
Write-Log "Running catch-up: $Python $CatchUp --catch-up --verify"
& $Python $CatchUp --catch-up --verify 2>&1 | ForEach-Object {
    Write-Log $_
    $_
}
$code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
Write-Log "Catch-up exit code: $code"
if ($code -ne 0) { exit $code }

$Manifest = Join-Path $ProjectRoot 'am_daily_dashboard\check_definitions_manifest.py'
if (Test-Path $Manifest) {
    Write-Log "Running manifest check (Slack alert on drift if configured)"
    & $Python $Manifest --slack 2>&1 | ForEach-Object {
        Write-Log $_
        $_
    }
}

if ($EnableAmBriefSlack) {
    $env:AM_BRIEF_SLACK_ENABLED = '1'
    $PostAm = Join-Path $ProjectRoot 'am_daily_dashboard\post_am_brief_slack.py'
    Write-Log "Running AM Brief Slack DMs: $PostAm --skip-catch-up"
    & $Python $PostAm --skip-catch-up 2>&1 | ForEach-Object {
        Write-Log $_
        $_
    }
    Write-Log "AM Brief Slack exit code: $LASTEXITCODE"
} else {
    Write-Log "AM Brief Slack disabled (pass -EnableAmBriefSlack to turn on)"
}

exit $code
